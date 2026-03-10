"""
DART OpenAPI Tool
재무제표 조회 + 공시 검색
API: https://opendart.fss.or.kr/
"""

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
    """DART에서 기업코드 XML을 다운로드하여 {기업명: corp_code} 딕셔너리 반환."""
    global _corp_code_cache
    if _corp_code_cache is not None:
        return _corp_code_cache

    with _cache_lock:
        if _corp_code_cache is not None:
            return _corp_code_cache

        url = f"{DART_BASE_URL}/corpCode.xml"
        resp = requests.get(url, params={"crtfc_key": DART_API_KEY}, timeout=30)
        resp.raise_for_status()

        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            xml_name = zf.namelist()[0]
            xml_data = zf.read(xml_name)

        root = ET.fromstring(xml_data)
        mapping = {}
        for item in root.iter("list"):
            corp_name = item.findtext("corp_name", "")
            corp_code = item.findtext("corp_code", "")
            if corp_name and corp_code:
                mapping[corp_name] = corp_code

        _corp_code_cache = mapping
    return _corp_code_cache


def resolve_corp_code(corp_name: str) -> str:
    """기업명으로 corp_code를 조회한다. 없으면 ValueError."""
    codes = _load_corp_codes()
    if corp_name in codes:
        return codes[corp_name]
    # 부분 매칭 시도
    matches = [name for name in codes if corp_name in name]
    if len(matches) == 1:
        return codes[matches[0]]
    if len(matches) > 1:
        raise ValueError(f"여러 기업이 매칭됩니다: {matches[:5]}")
    raise ValueError(f"'{corp_name}' 기업을 찾을 수 없습니다")


REPORT_CODES = {
    "annual": "11011",
    "q1": "11013",
    "half": "11012",
    "q3": "11014",
}


def dart_financials(corp_name: str, year: str, report_type: str = "annual") -> str:
    """DART API로 재무제표 주요계정을 조회한다."""
    corp_code = resolve_corp_code(corp_name)
    reprt_code = REPORT_CODES.get(report_type, "11011")

    resp = requests.get(
        f"{DART_BASE_URL}/fnlttSinglAcnt.json",
        params={
            "crtfc_key": DART_API_KEY,
            "corp_code": corp_code,
            "bsns_year": year,
            "reprt_code": reprt_code,
        },
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()

    if data.get("status") != "000":
        return f"DART API 오류: {data.get('message', '알 수 없는 오류')}"

    lines = [f"[{corp_name}] {year}년 재무제표 ({report_type})"]
    for item in data.get("list", []):
        name = item.get("account_nm", "")
        current = item.get("thstrm_amount", "")
        prev = item.get("frmtrm_amount", "")
        lines.append(f"  {name}: 당기 {current} / 전기 {prev}")

    return "\n".join(lines)


def dart_search(keyword: str, page_count: int = 10) -> str:
    """DART 공시 검색."""
    resp = requests.get(
        f"{DART_BASE_URL}/list.json",
        params={
            "crtfc_key": DART_API_KEY,
            "corp_name": keyword,
            "page_count": str(page_count),
        },
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()

    if data.get("status") != "000":
        return f"DART API 오류: {data.get('message', '알 수 없는 오류')}"

    total = data.get("total_count", 0)
    lines = [f"'{keyword}' 공시 검색 결과: {total}건"]
    for item in data.get("list", []):
        name = item.get("corp_name", "")
        report = item.get("report_nm", "")
        date = item.get("rcept_dt", "")
        lines.append(f"  [{date}] {name} - {report}")

    return "\n".join(lines)
