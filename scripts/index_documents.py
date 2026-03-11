"""오프라인 배치 인덱서 — DART 공시 → FAISS 인덱스 생성.

Usage:
    python scripts/index_documents.py --corps "삼성전자,LG화학" --years "2023,2024"
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import faiss
import numpy as np
import voyageai

from chunker import chunk_text
from dart_downloader import (
    download_document_zip,
    extract_html_from_zip,
    list_disclosures,
)
from html_parser import extract_text_from_html

DATA_DIR = Path(__file__).parent.parent / "data"
DOCS_DIR = DATA_DIR / "documents"
FAISS_DIR = DATA_DIR / "faiss"
CHECKPOINT_PATH = FAISS_DIR / "checkpoint.json"

EMBEDDING_MODEL = "voyage-3.5-lite"
BATCH_SIZE = 128  # Voyage AI 배치 크기
CHUNK_SIZE = 500
CHUNK_OVERLAP = 100

_TRANSIENT_ERRORS = ("429", "rate_limit", "RateLimitError", "timeout", "Timeout", "ConnectionError")


def _get_voyage_client() -> voyageai.Client:
    api_key = os.getenv("VOYAGE_API_KEY", "")
    if not api_key:
        raise ValueError("VOYAGE_API_KEY 환경변수가 설정되지 않았습니다")
    return voyageai.Client(api_key=api_key)


def _is_transient(e: Exception) -> bool:
    err = str(e)
    return any(tok in err for tok in _TRANSIENT_ERRORS)


def _batch_embed(client: voyageai.Client, texts: list[str], total_so_far: int = 0) -> list[list[float]]:
    """Voyage AI로 다수 텍스트를 배치 임베딩한다. 일시적 오류 재시도 포함."""
    all_embeddings = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        for attempt in range(5):
            try:
                result = client.embed(
                    batch,
                    model=EMBEDDING_MODEL,
                    input_type="document",
                )
                all_embeddings.extend(result.embeddings)
                done = total_so_far + len(all_embeddings)
                print(f"  임베딩 {done} 완료 (현재 배치 {len(all_embeddings)}/{len(texts)})", flush=True)
                break
            except Exception as e:
                if _is_transient(e) and attempt < 4:
                    wait = 2.0 * (2 ** attempt)
                    print(f"  일시적 오류({type(e).__name__}), {wait:.0f}초 대기 후 재시도 ({attempt+1}/5)...", flush=True)
                    time.sleep(wait)
                else:
                    raise
    return all_embeddings


# ---------------------------------------------------------------------------
# Checkpoint helpers
# ---------------------------------------------------------------------------

def _load_checkpoint() -> tuple[list[dict], list[list[float]]]:
    """체크포인트가 있으면 로드한다. 없으면 빈 리스트를 반환한다."""
    if not CHECKPOINT_PATH.exists():
        return [], []
    try:
        data = json.loads(CHECKPOINT_PATH.read_text())
        chunks = data.get("chunks", [])
        embeddings = data.get("embeddings", [])
        print(f"체크포인트 로드: {len(chunks)}개 청크, {len(embeddings)}개 임베딩", flush=True)
        return chunks, embeddings
    except Exception as e:
        print(f"체크포인트 로드 실패 ({e}), 처음부터 시작합니다.", flush=True)
        return [], []


def _save_checkpoint(chunks: list[dict], embeddings: list[list[float]]) -> None:
    """현재 진행 상태를 체크포인트 파일에 저장한다."""
    FAISS_DIR.mkdir(parents=True, exist_ok=True)
    tmp = CHECKPOINT_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps({"chunks": chunks, "embeddings": embeddings}, ensure_ascii=False))
    tmp.rename(CHECKPOINT_PATH)
    print(f"  체크포인트 저장: {len(chunks)}개 청크", flush=True)


def index_corp(
    client: voyageai.Client,
    corp_name: str,
    year: str,
    all_chunks: list[dict],
    all_embeddings: list[list[float]],
    max_chunks: int = 0,
) -> None:
    """단일 기업·연도의 공시를 다운로드하고 청크+임베딩을 누적한다."""
    existing_keys = {(c["corp_name"], c["year"], c["rcept_no"]) for c in all_chunks}

    print(f"\n[{corp_name}] {year}년 공시 목록 조회...", flush=True)
    disclosures = list_disclosures(corp_name, year)
    if not disclosures:
        print("  공시 없음, 건너뜀", flush=True)
        return

    for disc in disclosures:
        if max_chunks and len(all_chunks) >= max_chunks:
            print(f"  청크 수 제한({max_chunks}개) 도달, 중단", flush=True)
            break

        rcept_no = disc["rcept_no"]
        report_nm = disc["report_nm"]

        # 이미 처리된 공시는 건너뜀 (체크포인트 resume)
        if (corp_name, year, rcept_no) in existing_keys:
            print(f"  스킵(체크포인트): {report_nm} ({rcept_no})", flush=True)
            continue

        print(f"  다운로드: {report_nm} ({rcept_no})", flush=True)

        # ZIP 캐시 확인
        zip_path = DOCS_DIR / f"{corp_name}_{year}_{rcept_no}.zip"
        if zip_path.exists():
            zip_bytes = zip_path.read_bytes()
            print(f"    캐시 사용: {zip_path.name}", flush=True)
        else:
            try:
                zip_bytes = download_document_zip(rcept_no)
            except Exception as e:
                print(f"    다운로드 실패: {e}", flush=True)
                continue
            zip_path.write_bytes(zip_bytes)

        html_files = extract_html_from_zip(zip_bytes)
        if not html_files:
            print("    HTML 파일 없음, 건너뜀", flush=True)
            continue

        for filename, html_content in html_files:
            text = extract_text_from_html(html_content)
            if not text:
                continue

            chunks = chunk_text(text, CHUNK_SIZE, CHUNK_OVERLAP)
            for chunk in chunks:
                all_chunks.append({
                    "corp_name": corp_name,
                    "year": year,
                    "rcept_no": rcept_no,
                    "report_nm": report_nm,
                    "source_file": filename,
                    "text": chunk,
                })
                if max_chunks and len(all_chunks) >= max_chunks:
                    break
            if max_chunks and len(all_chunks) >= max_chunks:
                break

        print(f"    {len(html_files)}개 HTML → 청크 누적 {len(all_chunks)}개", flush=True)

    # 누적된 청크 중 아직 임베딩이 없는 것만 처리
    new_texts = [c["text"] for c in all_chunks[len(all_embeddings) :]]
    if new_texts:
        print(f"  임베딩 생성 ({len(new_texts)}개 청크)...", flush=True)
        new_embeddings = _batch_embed(client, new_texts, total_so_far=len(all_embeddings))
        all_embeddings.extend(new_embeddings)
        _save_checkpoint(all_chunks, all_embeddings)


def save_index(all_chunks: list[dict], all_embeddings: list[list[float]]) -> None:
    """FAISS 인덱스와 메타데이터를 원자적으로 저장한다."""
    if not all_embeddings:
        print("저장할 데이터 없음")
        return

    FAISS_DIR.mkdir(parents=True, exist_ok=True)

    vectors = np.array(all_embeddings, dtype=np.float32)
    dim = vectors.shape[1]
    index = faiss.IndexFlatIP(dim)  # Inner Product (코사인 유사도용 정규화 필요)
    faiss.normalize_L2(vectors)
    index.add(vectors)

    # 원자적 쓰기
    tmp_index = FAISS_DIR / "index.faiss.tmp"
    tmp_meta = FAISS_DIR / "metadata.json.tmp"

    faiss.write_index(index, str(tmp_index))

    metadata = [
        {k: v for k, v in chunk.items() if k != "text"}
        | {"chunk_id": i, "text": chunk["text"]}
        for i, chunk in enumerate(all_chunks)
    ]
    tmp_meta.write_text(json.dumps(metadata, ensure_ascii=False, indent=2))

    tmp_index.rename(FAISS_DIR / "index.faiss")
    tmp_meta.rename(FAISS_DIR / "metadata.json")

    print(f"\n인덱스 저장 완료: {len(all_chunks)}개 청크, 차원 {dim}")


def main():
    parser = argparse.ArgumentParser(description="DART 공시 배치 인덱서")
    parser.add_argument(
        "--corps", required=True, help="기업명 (쉼표 구분, 예: 삼성전자,LG화학)"
    )
    parser.add_argument(
        "--years", required=True, help="사업연도 (쉼표 구분, 예: 2023,2024)"
    )
    parser.add_argument(
        "--max-chunks", type=int, default=0, help="최대 청크 수 (0=무제한)"
    )
    args = parser.parse_args()

    corps = [c.strip() for c in args.corps.split(",")]
    years = [y.strip() for y in args.years.split(",")]

    client = _get_voyage_client()

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    FAISS_DIR.mkdir(parents=True, exist_ok=True)

    # 체크포인트에서 진행 상태 복원
    all_chunks, all_embeddings = _load_checkpoint()

    for corp_name in corps:
        for year in years:
            index_corp(client, corp_name, year, all_chunks, all_embeddings, args.max_chunks)

    save_index(all_chunks, all_embeddings)

    # 성공적으로 완료된 경우 체크포인트 삭제
    if CHECKPOINT_PATH.exists():
        CHECKPOINT_PATH.unlink()
        print("체크포인트 파일 삭제 완료", flush=True)


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent))
    main()
