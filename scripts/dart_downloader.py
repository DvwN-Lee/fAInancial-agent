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
