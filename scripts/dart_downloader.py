"""DART 공시 문서 다운로드 — ZIP → HTML 추출."""

import io
import os
import threading
import xml.etree.ElementTree as ET
import zipfile

import requests

DART_API_KEY = os.getenv("DART_API_KEY", "")
DART_BASE_URL = "https://opendart.fss.or.kr/api"

_corp_code_cache: dict[str, str] | None = None
_cache_lock = threading.Lock()


def _load_corp_codes() -> dict[str, str]:
    """DART 기업코드 XML을 다운로드하여 {기업명: corp_code} 딕셔너리 반환."""
    global _corp_code_cache
    if _corp_code_cache is not None:
        return _corp_code_cache
    with _cache_lock:
        if _corp_code_cache is not None:
            return _corp_code_cache
        resp = requests.get(
            f"{DART_BASE_URL}/corpCode.xml",
            params={"crtfc_key": DART_API_KEY},
            timeout=30,
        )
        resp.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            xml_data = zf.read(zf.namelist()[0])
        root = ET.fromstring(xml_data)
        mapping = {}
        for item in root.iter("list"):
            name = item.findtext("corp_name", "")
            code = item.findtext("corp_code", "")
            if name and code:
                mapping[name] = code
        _corp_code_cache = mapping
    return _corp_code_cache


def _resolve_corp_code(corp_name: str) -> str:
    """기업명 → corp_code 변환. 정확 매칭 후 부분 매칭 시도."""
    codes = _load_corp_codes()
    if corp_name in codes:
        return codes[corp_name]
    matches = [n for n in codes if corp_name in n]
    if len(matches) == 1:
        return codes[matches[0]]
    if len(matches) > 1:
        raise ValueError(f"여러 기업이 매칭됩니다: {matches[:5]}")
    raise ValueError(f"'{corp_name}' 기업을 찾을 수 없습니다")


def list_disclosures(corp_name: str, year: str) -> list[dict]:
    """DART API로 공시 목록을 조회하여 rcept_no 리스트를 반환한다."""
    if not DART_API_KEY:
        raise ValueError("DART_API_KEY 환경변수가 설정되지 않았습니다")

    corp_code = _resolve_corp_code(corp_name)

    resp = requests.get(
        f"{DART_BASE_URL}/list.json",
        params={
            "crtfc_key": DART_API_KEY,
            "corp_code": corp_code,
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
