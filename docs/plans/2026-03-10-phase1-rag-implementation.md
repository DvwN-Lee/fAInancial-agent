# Phase 1-1 RAG Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** DART 공시 원문(HTML)을 벡터화하여 자연어 검색할 수 있는 RAG 파이프라인을 MCP Tool로 제공한다.

**Architecture:** 오프라인 CLI 인덱서(DART ZIP→HTML 파싱→청킹→Voyage AI 배치 임베딩→FAISS)와 온라인 MCP Tool(FAISS 검색→청크 반환)로 분리. Agent 코드 변경 제로.

**Tech Stack:** Python 3.12, BeautifulSoup4, faiss-cpu, voyageai (voyage-finance-2), RAGAS, FastMCP

**Design Doc:** `docs/plans/2026-03-10-phase1-rag-design.md`

---

### Task 1: 프로젝트 구조 준비

**Files:**
- Create: `data/.gitkeep`
- Create: `data/documents/.gitkeep`
- Create: `data/faiss/.gitkeep`
- Create: `data/eval/.gitkeep`
- Create: `scripts/__init__.py`
- Create: `scripts/requirements.txt`
- Modify: `mcp_server/requirements.txt`
- Modify: `pyproject.toml`
- Modify: `.gitignore`

**Step 1: 디렉터리 구조 생성**

```bash
mkdir -p data/documents data/faiss data/eval scripts
touch data/.gitkeep data/documents/.gitkeep data/faiss/.gitkeep data/eval/.gitkeep
touch scripts/__init__.py
```

**Step 2: scripts/requirements.txt 생성**

```
beautifulsoup4>=4.12.0
lxml>=5.0.0
faiss-cpu>=1.9.0
voyageai>=0.3.0
ragas>=0.2.0
requests>=2.31.0
```

**Step 3: mcp_server/requirements.txt 수정**

`mcp_server/requirements.txt`에 추가:
```
faiss-cpu>=1.9.0
voyageai>=0.3.0
numpy>=1.26.0
```

기존 내용 유지하여 최종:
```
mcp[cli]>=1.6.0
requests>=2.31.0
finance-datareader>=0.9.0
faiss-cpu>=1.9.0
voyageai>=0.3.0
numpy>=1.26.0
```

**Step 4: pyproject.toml에 scripts 의존성 그룹 추가**

`pyproject.toml`의 `[project.optional-dependencies]` 섹션에 추가:
```toml
[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.24.0",
    "httpx>=0.27.0",
]
scripts = [
    "beautifulsoup4>=4.12.0",
    "lxml>=5.0.0",
    "faiss-cpu>=1.9.0",
    "voyageai>=0.3.0",
    "ragas>=0.2.0",
    "requests>=2.31.0",
]
```

**Step 5: .gitignore에 data 디렉터리 패턴 추가**

`.gitignore` 하단에 추가:
```
# --- Data (인덱스·다운로드 파일은 버전 관리 제외) ---
data/documents/*
data/faiss/*
data/eval/results_*.json
!data/**/.gitkeep
```

**Step 6: .env.example 업데이트 (존재 시)**

`.env.example`에 추가:
```
VOYAGE_API_KEY=your-voyage-api-key
```

**Step 7: 커밋**

```bash
git add data/ scripts/requirements.txt scripts/__init__.py mcp_server/requirements.txt pyproject.toml .gitignore
git commit -m "chore: Phase 1 RAG 프로젝트 구조 준비"
```

---

### Task 2: HTML 파서 모듈

**Files:**
- Create: `scripts/html_parser.py`
- Create: `tests/scripts/__init__.py`
- Create: `tests/scripts/test_html_parser.py`
- Create: `tests/scripts/fixtures/sample_disclosure.html`

**Step 1: 테스트 픽스처 작성**

`tests/scripts/fixtures/sample_disclosure.html`:
```html
<html>
<head><title>사업보고서</title></head>
<body>
<div class="xforms">
  <p>1. 사업의 개요</p>
  <p>당사는 반도체 사업을 주력으로 영위하고 있습니다.</p>
  <table>
    <tr><td>매출액</td><td>100,000</td></tr>
    <tr><td>영업이익</td><td>20,000</td></tr>
  </table>
  <p>2. 주요 위험 요인</p>
  <p>반도체 수급 변동에 따른 가격 하락 위험이 존재합니다.</p>
</div>
</body>
</html>
```

**Step 2: 실패 테스트 작성**

`tests/scripts/test_html_parser.py`:
```python
from pathlib import Path

from scripts.html_parser import extract_text_from_html

FIXTURE_DIR = Path(__file__).parent / "fixtures"


def test_extract_text_from_html():
    html_content = (FIXTURE_DIR / "sample_disclosure.html").read_text()
    text = extract_text_from_html(html_content)

    assert "반도체 사업을 주력으로" in text
    assert "반도체 수급 변동" in text
    assert "매출액" in text


def test_extract_text_strips_tags():
    html_content = "<html><body><p>테스트 <b>텍스트</b></p></body></html>"
    text = extract_text_from_html(html_content)

    assert "<p>" not in text
    assert "<b>" not in text
    assert "테스트 텍스트" in text


def test_extract_text_empty_html():
    text = extract_text_from_html("")
    assert text == ""
```

`tests/scripts/__init__.py`: 빈 파일

**Step 3: 테스트 실행 — 실패 확인**

```bash
pytest tests/scripts/test_html_parser.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.html_parser'`

**Step 4: 최소 구현**

`scripts/html_parser.py`:
```python
"""DART 공시 HTML → 텍스트 추출."""

from bs4 import BeautifulSoup


def extract_text_from_html(html_content: str) -> str:
    """HTML 문자열에서 본문 텍스트를 추출한다.

    DART 공시 ZIP 내 *.html 파일의 내용을 받아
    태그를 제거하고 순수 텍스트만 반환한다.
    """
    if not html_content:
        return ""

    soup = BeautifulSoup(html_content, "lxml")

    for tag in soup(["script", "style", "head"]):
        tag.decompose()

    text = soup.get_text(separator="\n")

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)
```

**Step 5: 테스트 실행 — 통과 확인**

```bash
pytest tests/scripts/test_html_parser.py -v
```
Expected: 3 passed

**Step 6: conftest.py에 scripts 경로 추가**

`tests/conftest.py` 수정 — 기존 2줄 뒤에 추가:
```python
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
```

**Step 7: 커밋**

```bash
git add scripts/html_parser.py tests/scripts/ tests/conftest.py
git commit -m "feat: DART 공시 HTML→텍스트 추출 모듈"
```

---

### Task 3: 청킹 모듈

**Files:**
- Create: `scripts/chunker.py`
- Create: `tests/scripts/test_chunker.py`

**Step 1: 실패 테스트 작성**

`tests/scripts/test_chunker.py`:
```python
from scripts.chunker import chunk_text


def test_chunk_text_basic():
    text = "가" * 1000
    chunks = chunk_text(text, chunk_size=500, overlap=100)

    assert len(chunks) == 3  # 500 + 500 + 끝 (overlap 고려)
    assert all(len(c) <= 500 for c in chunks)


def test_chunk_text_short():
    text = "짧은 텍스트"
    chunks = chunk_text(text, chunk_size=500, overlap=100)

    assert len(chunks) == 1
    assert chunks[0] == "짧은 텍스트"


def test_chunk_text_overlap():
    text = "가" * 600
    chunks = chunk_text(text, chunk_size=500, overlap=100)

    assert len(chunks) == 2
    # 첫 청크 끝 100자 == 둘째 청크 앞 100자
    assert chunks[0][-100:] == chunks[1][:100]


def test_chunk_text_empty():
    chunks = chunk_text("", chunk_size=500, overlap=100)
    assert chunks == []
```

**Step 2: 테스트 실행 — 실패 확인**

```bash
pytest tests/scripts/test_chunker.py -v
```
Expected: FAIL

**Step 3: 최소 구현**

`scripts/chunker.py`:
```python
"""텍스트 청킹 — 고정 크기 + 오버랩."""


def chunk_text(
    text: str, chunk_size: int = 500, overlap: int = 100
) -> list[str]:
    """텍스트를 고정 크기 청크로 분할한다.

    Args:
        text: 분할할 텍스트
        chunk_size: 청크 최대 길이 (글자 수)
        overlap: 청크 간 오버랩 길이 (글자 수)
    """
    if not text:
        return []

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap

    return chunks
```

**Step 4: 테스트 실행 — 통과 확인**

```bash
pytest tests/scripts/test_chunker.py -v
```
Expected: 4 passed

**Step 5: 커밋**

```bash
git add scripts/chunker.py tests/scripts/test_chunker.py
git commit -m "feat: 텍스트 청킹 모듈 (고정 크기 + 오버랩)"
```

---

### Task 4: DART 문서 다운로더 모듈

**Files:**
- Create: `scripts/dart_downloader.py`
- Create: `tests/scripts/test_dart_downloader.py`

**Step 1: 실패 테스트 작성**

`tests/scripts/test_dart_downloader.py`:
```python
import io
import zipfile

import pytest

from scripts.dart_downloader import extract_html_from_zip, list_disclosures


def _make_test_zip(files: dict[str, str]) -> bytes:
    """테스트용 ZIP 바이트를 생성한다."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buf.getvalue()


def test_extract_html_from_zip():
    zip_bytes = _make_test_zip({
        "document.xml": "<manifest/>",
        "section1.html": "<p>본문1</p>",
        "section2.htm": "<p>본문2</p>",
        "data.xbrl": "<xbrl/>",
    })
    html_files = extract_html_from_zip(zip_bytes)

    assert len(html_files) == 2
    names = [name for name, _ in html_files]
    assert "section1.html" in names
    assert "section2.htm" in names


def test_extract_html_from_zip_no_html():
    zip_bytes = _make_test_zip({
        "document.xml": "<manifest/>",
        "data.xbrl": "<xbrl/>",
    })
    html_files = extract_html_from_zip(zip_bytes)
    assert html_files == []


def test_list_disclosures_missing_api_key(monkeypatch):
    monkeypatch.delenv("DART_API_KEY", raising=False)
    with pytest.raises(ValueError, match="DART_API_KEY"):
        list_disclosures("삼성전자", "2024")
```

**Step 2: 테스트 실행 — 실패 확인**

```bash
pytest tests/scripts/test_dart_downloader.py -v
```
Expected: FAIL

**Step 3: 최소 구현**

`scripts/dart_downloader.py`:
```python
"""DART 공시 문서 다운로드 — ZIP → HTML 추출."""

import io
import os
import zipfile

import requests

DART_API_KEY = os.getenv("DART_API_KEY", "")
DART_BASE_URL = "https://opendart.fss.or.kr/api"


def list_disclosures(corp_name: str, year: str) -> list[dict]:
    """DART API로 공시 목록을 조회하여 rcept_no 리스트를 반환한다."""
    if not DART_API_KEY:
        raise ValueError("DART_API_KEY 환경변수가 설정되지 않았습니다")

    resp = requests.get(
        f"{DART_BASE_URL}/list.json",
        params={
            "crtfc_key": DART_API_KEY,
            "corp_name": corp_name,
            "bgn_de": f"{year}0101",
            "end_de": f"{year}1231",
            "pblntf_ty": "A",  # 정기공시
            "page_count": "100",
        },
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()

    if data.get("status") != "000":
        return []

    return [
        {
            "rcept_no": item["rcept_no"],
            "report_nm": item.get("report_nm", ""),
            "corp_name": item.get("corp_name", ""),
            "rcept_dt": item.get("rcept_dt", ""),
        }
        for item in data.get("list", [])
    ]


def download_document_zip(rcept_no: str) -> bytes:
    """DART document.xml API로 공시 원문 ZIP을 다운로드한다."""
    if not DART_API_KEY:
        raise ValueError("DART_API_KEY 환경변수가 설정되지 않았습니다")

    resp = requests.get(
        f"{DART_BASE_URL}/document.xml",
        params={
            "crtfc_key": DART_API_KEY,
            "rcept_no": rcept_no,
        },
        timeout=60,
    )
    resp.raise_for_status()
    return resp.content


def extract_html_from_zip(zip_bytes: bytes) -> list[tuple[str, str]]:
    """ZIP 바이트에서 *.html, *.htm 파일을 추출한다.

    Returns:
        [(파일명, HTML 내용), ...] 리스트
    """
    html_files = []
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        for name in zf.namelist():
            lower = name.lower()
            if lower.endswith(".html") or lower.endswith(".htm"):
                content = zf.read(name).decode("utf-8", errors="replace")
                html_files.append((name, content))
    return html_files
```

**Step 4: 테스트 실행 — 통과 확인**

```bash
pytest tests/scripts/test_dart_downloader.py -v
```
Expected: 3 passed

**Step 5: 커밋**

```bash
git add scripts/dart_downloader.py tests/scripts/test_dart_downloader.py
git commit -m "feat: DART 공시 ZIP 다운로드 및 HTML 추출 모듈"
```

---

### Task 5: 배치 인덱서 CLI

**Files:**
- Create: `scripts/index_documents.py`

**Step 1: 구현**

`scripts/index_documents.py`:
```python
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

EMBEDDING_MODEL = "voyage-finance-2"
BATCH_SIZE = 128  # Voyage AI 배치 크기
CHUNK_SIZE = 500
CHUNK_OVERLAP = 100


def _get_voyage_client() -> voyageai.Client:
    api_key = os.getenv("VOYAGE_API_KEY", "")
    if not api_key:
        raise ValueError("VOYAGE_API_KEY 환경변수가 설정되지 않았습니다")
    return voyageai.Client(api_key=api_key)


def _batch_embed(client: voyageai.Client, texts: list[str]) -> list[list[float]]:
    """Voyage AI로 다수 텍스트를 배치 임베딩한다."""
    all_embeddings = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        result = client.embed(
            batch,
            model=EMBEDDING_MODEL,
            input_type="document",
        )
        all_embeddings.extend(result.embeddings)
        print(f"  임베딩 {len(all_embeddings)}/{len(texts)} 완료")
    return all_embeddings


def index_corp(
    client: voyageai.Client,
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

    client = _get_voyage_client()

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
```

**Step 2: 수동 테스트 (API 키 필요)**

```bash
cd /Users/idongju/Desktop/Git/fAInancial-agent
python scripts/index_documents.py --corps "삼성전자" --years "2024"
```
Expected: `data/faiss/index.faiss` + `data/faiss/metadata.json` 생성

**Step 3: 커밋**

```bash
git add scripts/index_documents.py
git commit -m "feat: DART 공시 배치 인덱서 CLI"
```

---

### Task 6: RAG 검색 모듈 (MCP Server)

**Files:**
- Create: `mcp_server/rag_search.py`
- Create: `tests/mcp_server/test_rag_search.py`

**Step 1: 실패 테스트 작성**

`tests/mcp_server/test_rag_search.py`:
```python
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import faiss
import numpy as np
import pytest

from rag_search import _load_metadata, rag_search


@pytest.fixture
def fake_faiss_dir(tmp_path):
    """3개 청크를 가진 테스트용 FAISS 인덱스를 생성한다."""
    dim = 1024
    vectors = np.random.rand(3, dim).astype(np.float32)
    faiss.normalize_L2(vectors)
    index = faiss.IndexFlatIP(dim)
    index.add(vectors)
    faiss.write_index(index, str(tmp_path / "index.faiss"))

    metadata = [
        {"chunk_id": 0, "corp_name": "삼성전자", "year": "2024",
         "text": "반도체 수급 변동에 따른 위험"},
        {"chunk_id": 1, "corp_name": "삼성전자", "year": "2023",
         "text": "메모리 반도체 시장 전망"},
        {"chunk_id": 2, "corp_name": "LG화학", "year": "2024",
         "text": "배터리 사업 확장 계획"},
    ]
    (tmp_path / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False)
    )
    return tmp_path


def test_load_metadata(fake_faiss_dir):
    meta = _load_metadata(fake_faiss_dir / "metadata.json")
    assert len(meta) == 3
    assert meta[0]["corp_name"] == "삼성전자"


def test_rag_search_filters_by_corp(fake_faiss_dir):
    """corp_name 필터가 동작하는지 확인."""
    fake_embedding = np.random.rand(1024).astype(np.float32).tolist()

    with patch("rag_search.FAISS_DIR", fake_faiss_dir), \
         patch("rag_search._embed_query", return_value=fake_embedding), \
         patch("rag_search._index", None), \
         patch("rag_search._metadata", None):
        result = rag_search("위험 요인", corp_name="LG화학")

    assert "LG화학" in result
    assert "배터리" in result


def test_rag_search_no_index(tmp_path):
    """인덱스 미존재 시 명시적 에러."""
    with patch("rag_search.FAISS_DIR", tmp_path):
        result = rag_search("테스트")

    assert "인덱스" in result or "없습니다" in result
```

**Step 2: 테스트 실행 — 실패 확인**

```bash
pytest tests/mcp_server/test_rag_search.py -v
```
Expected: FAIL

**Step 3: 최소 구현**

`mcp_server/rag_search.py`:
```python
"""RAG 검색 — FAISS 인덱스 기반 시맨틱 검색."""

import json
import os
from pathlib import Path

import faiss
import numpy as np
import voyageai

FAISS_DIR = Path(__file__).parent.parent / "data" / "faiss"
EMBEDDING_MODEL = "voyage-finance-2"
TOP_K = 5
SEARCH_MULTIPLIER = 3  # post-filter용 오버페칭 배수

_index: faiss.Index | None = None
_metadata: list[dict] | None = None
_voyage_client: voyageai.Client | None = None


def _get_voyage_client() -> voyageai.Client:
    global _voyage_client
    if _voyage_client is None:
        _voyage_client = voyageai.Client(api_key=os.getenv("VOYAGE_API_KEY", ""))
    return _voyage_client


def _get_index() -> faiss.Index:
    """FAISS 인덱스를 lazy load한다. 1회 로드 후 메모리 유지."""
    global _index
    if _index is None:
        index_path = FAISS_DIR / "index.faiss"
        if not index_path.exists():
            raise FileNotFoundError(
                "FAISS 인덱스가 없습니다. "
                "scripts/index_documents.py를 먼저 실행하세요."
            )
        _index = faiss.read_index(str(index_path))
    return _index


def _load_metadata(path: Path | None = None) -> list[dict]:
    """메타데이터를 로드한다."""
    global _metadata
    if _metadata is None:
        meta_path = path or (FAISS_DIR / "metadata.json")
        if not meta_path.exists():
            raise FileNotFoundError("metadata.json이 없습니다.")
        _metadata = json.loads(meta_path.read_text())
    return _metadata


def _embed_query(query: str) -> list[float]:
    """쿼리를 임베딩한다."""
    client = _get_voyage_client()
    result = client.embed(
        [query],
        model=EMBEDDING_MODEL,
        input_type="query",
    )
    return result.embeddings[0]


def rag_search(
    query: str,
    corp_name: str | None = None,
    year: str | None = None,
    top_k: int = TOP_K,
) -> str:
    """공시 문서에서 시맨틱 검색을 수행한다."""
    try:
        index = _get_index()
        metadata = _load_metadata()
    except FileNotFoundError as e:
        return str(e)

    query_vec = np.array([_embed_query(query)], dtype=np.float32)
    faiss.normalize_L2(query_vec)

    # 오버페칭 후 post-filter
    search_k = min(top_k * SEARCH_MULTIPLIER, index.ntotal)
    distances, indices = index.search(query_vec, search_k)

    results = []
    for dist, idx in zip(distances[0], indices[0]):
        if idx == -1:
            continue
        meta = metadata[idx]

        # post-filter
        if corp_name and meta.get("corp_name") != corp_name:
            continue
        if year and meta.get("year") != year:
            continue

        results.append((dist, meta))
        if len(results) >= top_k:
            break

    if not results:
        filters = []
        if corp_name:
            filters.append(f"기업: {corp_name}")
        if year:
            filters.append(f"연도: {year}")
        filter_str = ", ".join(filters) if filters else "전체"
        return f"검색 결과 없음 ({filter_str})"

    lines = [f"'{query}' 관련 공시 내용 ({len(results)}건):"]
    for i, (score, meta) in enumerate(results, 1):
        lines.append(f"\n--- [{i}] 유사도: {score:.3f} ---")
        lines.append(f"기업: {meta.get('corp_name', '')}")
        lines.append(f"연도: {meta.get('year', '')}")
        lines.append(f"보고서: {meta.get('report_nm', '')}")
        lines.append(f"출처: {meta.get('source_file', '')}")
        lines.append(f"내용: {meta.get('text', '')}")

    return "\n".join(lines)
```

**Step 4: 테스트 실행 — 통과 확인**

```bash
pytest tests/mcp_server/test_rag_search.py -v
```
Expected: 3 passed

**Step 5: 커밋**

```bash
git add mcp_server/rag_search.py tests/mcp_server/test_rag_search.py
git commit -m "feat: RAG 검색 모듈 (FAISS + post-filter)"
```

---

### Task 7: MCP Tool 등록 + Docker 볼륨 마운트

**Files:**
- Modify: `mcp_server/main.py:9` — import 추가, Tool 등록
- Modify: `docker-compose.yml` — data/ 볼륨 마운트

**Step 1: mcp_server/main.py 수정**

`mcp_server/main.py`의 import 블록(line 9)에 추가:
```python
from rag_search import rag_search
```

`get_stock_price` Tool 뒤(line 47 이후)에 추가:
```python
@mcp.tool()
def search_documents(
    query: str,
    corp_name: str | None = None,
    year: str | None = None,
) -> str:
    """공시 문서에서 관련 내용을 검색합니다.

    Args:
        query: 검색 질문 (예: 사업 위험 요인, 주요 투자 계획)
        corp_name: 기업명 필터 (예: 삼성전자). 없으면 전체 검색
        year: 사업연도 필터 (예: 2024). 없으면 전체 연도 검색
    """
    return rag_search(query, corp_name, year)
```

**Step 2: docker-compose.yml 수정**

`mcp-server` 서비스에 volumes 추가:
```yaml
services:
  mcp-server:
    build: ./mcp_server
    ports:
      - "8001:8001"
    env_file:
      - .env
    volumes:
      - ./data/faiss:/app/data/faiss:ro
    healthcheck:
      test: ["CMD", "python", "-c", "import socket; s=socket.create_connection(('localhost',8001),timeout=3); s.close()"]
      interval: 10s
      timeout: 5s
      retries: 3
      start_period: 10s
    restart: unless-stopped
```

**Step 3: 기존 테스트 통과 확인**

```bash
pytest tests/ -v
```
Expected: 기존 테스트 전부 통과

**Step 4: 커밋**

```bash
git add mcp_server/main.py docker-compose.yml
git commit -m "feat: search_documents MCP Tool 등록 + Docker 볼륨 마운트"
```

---

### Task 8: E2E 통합 테스트

**Files:**
- Create: `tests/mcp_server/test_rag_e2e.py`

**Step 1: 실패 테스트 작성**

`tests/mcp_server/test_rag_e2e.py`:
```python
"""E2E 테스트 — search_documents MCP Tool이 정상 등록되었는지 확인."""


def test_search_documents_tool_registered():
    """search_documents가 MCP Tool로 등록되어 있는지 확인."""
    from main import mcp

    tool_names = [t.name for t in mcp._tool_manager.list_tools()]
    assert "search_documents" in tool_names


def test_search_documents_tool_has_params():
    """search_documents Tool의 파라미터가 올바른지 확인."""
    from main import mcp

    tools = mcp._tool_manager.list_tools()
    search_tool = next(t for t in tools if t.name == "search_documents")

    schema = search_tool.inputSchema
    props = schema.get("properties", {})
    assert "query" in props
    assert "corp_name" in props
    assert "year" in props
```

**Step 2: 테스트 실행 — 통과 확인**

```bash
pytest tests/mcp_server/test_rag_e2e.py -v
```
Expected: 2 passed

**Step 3: 커밋**

```bash
git add tests/mcp_server/test_rag_e2e.py
git commit -m "test: search_documents MCP Tool 등록 E2E 테스트"
```

---

### Task 9: RAGAS 평가 스크립트

**Files:**
- Create: `scripts/evaluate_rag.py`
- Create: `data/eval/qa_set.json`

**Step 1: 평가 데이터셋 작성**

`data/eval/qa_set.json`:
```json
[
  {
    "question": "삼성전자 2024년 사업보고서에서 주요 사업 위험은 무엇인가?",
    "ground_truth": "반도체 수급 변동, 환율 리스크, 글로벌 경기 둔화에 따른 수요 감소 위험",
    "corp_name": "삼성전자",
    "year": "2024"
  },
  {
    "question": "삼성전자 2024년 주요 투자 계획은?",
    "ground_truth": "반도체 설비 투자, HBM 생산 능력 확대, 파운드리 기술 고도화",
    "corp_name": "삼성전자",
    "year": "2024"
  },
  {
    "question": "삼성전자 2024년 매출 구성은?",
    "ground_truth": "DS 부문(반도체), DX 부문(모바일·가전), SDC, 하만 등으로 구성",
    "corp_name": "삼성전자",
    "year": "2024"
  },
  {
    "question": "삼성전자 2024년 연구개발 현황은?",
    "ground_truth": "반도체 미세공정, AI 반도체, 디스플레이 기술 등 연구개발 투자",
    "corp_name": "삼성전자",
    "year": "2024"
  },
  {
    "question": "삼성전자 2024년 임직원 현황은?",
    "ground_truth": "국내외 임직원 수, 평균 근속 연수, 부문별 인력 현황",
    "corp_name": "삼성전자",
    "year": "2024"
  }
]
```

**Step 2: 평가 스크립트 구현**

`scripts/evaluate_rag.py`:
```python
"""RAGAS 평가 스크립트 — RAG 품질 측정.

Usage:
    python scripts/evaluate_rag.py

측정 한계: 5~10개 샘플은 방향성 확인 초기 벤치마크 목적.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

from google import genai
from ragas import evaluate
from ragas.dataset_schema import EvaluationDataset, SingleTurnSample
from ragas.llms import llm_factory
from ragas.metrics import (
    Faithfulness,
    LLMContextPrecisionWithReference,
    ResponseRelevancy,
)

# scripts/ 경로 추가
sys.path.insert(0, str(Path(__file__).parent))

from rag_search_client import search_documents_local

DATA_DIR = Path(__file__).parent.parent / "data"
EVAL_DIR = DATA_DIR / "eval"

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


def _get_genai_client() -> genai.Client:
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        raise ValueError("GEMINI_API_KEY 환경변수가 설정되지 않았습니다")
    return genai.Client(api_key=api_key)


def _generate_answer(client: genai.Client, question: str, contexts: list[str]) -> str:
    """질문 + 검색된 컨텍스트로 답변을 생성한다."""
    context_text = "\n\n---\n\n".join(contexts)
    prompt = (
        f"다음 공시 문서 내용을 바탕으로 질문에 답변하세요.\n\n"
        f"[공시 내용]\n{context_text}\n\n"
        f"[질문]\n{question}"
    )
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
    )
    return response.text or ""


def main():
    qa_path = EVAL_DIR / "qa_set.json"
    if not qa_path.exists():
        print(f"평가 데이터셋 없음: {qa_path}")
        return

    qa_set = json.loads(qa_path.read_text())
    client = _get_genai_client()

    samples = []
    for qa in qa_set:
        question = qa["question"]
        ground_truth = qa["ground_truth"]
        corp_name = qa.get("corp_name")
        year = qa.get("year")

        # RAG 검색
        contexts = search_documents_local(question, corp_name, year)

        # 답변 생성
        answer = _generate_answer(client, question, contexts)

        samples.append(
            SingleTurnSample(
                user_input=question,
                response=answer,
                retrieved_contexts=contexts,
                reference=ground_truth,
            )
        )
        print(f"  처리: {question[:30]}...")

    dataset = EvaluationDataset(samples=samples)

    # RAGAS 평가 (Gemini LLM 사용)
    evaluator_llm = llm_factory("gemini-2.0-flash", provider="google")

    metrics = [
        Faithfulness(llm=evaluator_llm),
        ResponseRelevancy(llm=evaluator_llm),
        LLMContextPrecisionWithReference(llm=evaluator_llm),
    ]

    result = evaluate(dataset=dataset, metrics=metrics)

    # 결과 저장
    timestamp = datetime.now().strftime("%Y%m%d")
    result_path = EVAL_DIR / f"results_{timestamp}.json"
    result_dict = {
        "date": timestamp,
        "sample_count": len(qa_set),
        "metrics": {
            "faithfulness": result["faithfulness"],
            "answer_relevancy": result["answer_relevancy"],
            "context_precision": result["llm_context_precision_with_reference"],
        },
        "note": "방향성 확인 초기 벤치마크 (5~10개 샘플)",
    }
    result_path.write_text(json.dumps(result_dict, ensure_ascii=False, indent=2))

    print(f"\n=== RAGAS 평가 결과 ===")
    for metric, value in result_dict["metrics"].items():
        print(f"  {metric}: {value:.3f}")
    print(f"\n결과 저장: {result_path}")


if __name__ == "__main__":
    main()
```

**Step 3: RAG 검색 로컬 클라이언트 (MCP 없이 직접 호출)**

`scripts/rag_search_client.py`:
```python
"""RAGAS 평가용 — MCP 없이 rag_search를 직접 호출하는 래퍼."""

import sys
from pathlib import Path

# mcp_server/ 모듈 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent / "mcp_server"))

from rag_search import rag_search as _rag_search


def search_documents_local(
    query: str,
    corp_name: str | None = None,
    year: str | None = None,
) -> list[str]:
    """rag_search를 호출하고 청크 텍스트 리스트로 반환한다."""
    result = _rag_search(query, corp_name, year)

    # "내용: ..." 라인만 추출하여 contexts 리스트로 반환
    contexts = []
    for line in result.split("\n"):
        if line.startswith("내용: "):
            contexts.append(line[4:])

    return contexts if contexts else [result]
```

**Step 4: 커밋**

```bash
git add scripts/evaluate_rag.py scripts/rag_search_client.py data/eval/qa_set.json
git commit -m "feat: RAGAS 평가 스크립트 + 초기 평가 데이터셋"
```

---

### Task 10: 전체 통합 검증 + 최종 커밋

**Step 1: 전체 테스트 실행**

```bash
pytest tests/ -v
```
Expected: 모든 테스트 통과

**Step 2: Docker Compose 빌드 확인**

```bash
docker compose build
```
Expected: mcp-server, agent 이미지 빌드 성공

**Step 3: 린트/타입 확인 (선택)**

```bash
python -m py_compile mcp_server/rag_search.py
python -m py_compile scripts/index_documents.py
python -m py_compile scripts/evaluate_rag.py
```
Expected: 에러 없음

**Step 4: 최종 커밋**

```bash
git add -A
git commit -m "chore: Phase 1-1 RAG 전체 통합 검증"
```
