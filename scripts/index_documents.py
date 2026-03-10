"""오프라인 배치 인덱서 — DART 공시 → FAISS 인덱스 생성.

Usage:
    python scripts/index_documents.py --corps "삼성전자,LG화학" --years "2023,2024"
"""

import argparse
import json
import os
import sys
from pathlib import Path

import faiss
import numpy as np
from google import genai

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

EMBEDDING_MODEL = "text-embedding-004"
BATCH_SIZE = 100  # batch_embed_contents 1회당 텍스트 수
CHUNK_SIZE = 500
CHUNK_OVERLAP = 100


def _get_genai_client() -> genai.Client:
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        raise ValueError("GEMINI_API_KEY 환경변수가 설정되지 않았습니다")
    return genai.Client(api_key=api_key)


def _batch_embed(client: genai.Client, texts: list[str]) -> list[list[float]]:
    """batch_embed_contents로 다수 텍스트를 한 번에 임베딩한다."""
    all_embeddings = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        result = client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=batch,
        )
        all_embeddings.extend([e.values for e in result.embeddings])
        print(f"  임베딩 {len(all_embeddings)}/{len(texts)} 완료")
    return all_embeddings


def index_corp(
    client: genai.Client,
    corp_name: str,
    year: str,
    all_chunks: list[dict],
    all_embeddings: list[list[float]],
) -> None:
    """단일 기업·연도의 공시를 다운로드하고 청크+임베딩을 누적한다."""
    print(f"\n[{corp_name}] {year}년 공시 목록 조회...")
    disclosures = list_disclosures(corp_name, year)
    if not disclosures:
        print(f"  공시 없음, 건너뜀")
        return

    for disc in disclosures:
        rcept_no = disc["rcept_no"]
        report_nm = disc["report_nm"]
        print(f"  다운로드: {report_nm} ({rcept_no})")

        try:
            zip_bytes = download_document_zip(rcept_no)
        except Exception as e:
            print(f"    다운로드 실패: {e}")
            continue

        # ZIP 저장 (캐시)
        zip_path = DOCS_DIR / f"{corp_name}_{year}_{rcept_no}.zip"
        zip_path.write_bytes(zip_bytes)

        html_files = extract_html_from_zip(zip_bytes)
        if not html_files:
            print(f"    HTML 파일 없음, 건너뜀")
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

        print(f"    {len(html_files)}개 HTML → 청크 누적 {len(all_chunks)}개")

    # 누적된 청크 임베딩
    new_texts = [c["text"] for c in all_chunks[len(all_embeddings) :]]
    if new_texts:
        print(f"  임베딩 생성 ({len(new_texts)}개 청크)...")
        new_embeddings = _batch_embed(client, new_texts)
        all_embeddings.extend(new_embeddings)


def save_index(
    all_chunks: list[dict], all_embeddings: list[list[float]]
) -> None:
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

    # rename (POSIX 원자적)
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
    args = parser.parse_args()

    corps = [c.strip() for c in args.corps.split(",")]
    years = [y.strip() for y in args.years.split(",")]

    client = _get_genai_client()

    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    all_chunks: list[dict] = []
    all_embeddings: list[list[float]] = []

    for corp_name in corps:
        for year in years:
            index_corp(client, corp_name, year, all_chunks, all_embeddings)

    save_index(all_chunks, all_embeddings)


if __name__ == "__main__":
    # scripts/ 디렉터리를 path에 추가 (모듈 import 용)
    sys.path.insert(0, str(Path(__file__).parent))
    main()
