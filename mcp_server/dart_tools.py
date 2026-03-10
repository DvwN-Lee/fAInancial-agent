"""
DART OpenAPI Tool
재무제표 조회 + 공시 검색
API: https://opendart.fss.or.kr/
"""

import io
import os
import xml.etree.ElementTree as ET
import zipfile

import requests

DART_API_KEY = os.getenv("DART_API_KEY", "")
DART_BASE_URL = "https://opendart.fss.or.kr/api"

_corp_code_cache: dict[str, str] | None = None


def _load_corp_codes() -> dict[str, str]:
    """DART에서 기업코드 XML을 다운로드하여 {기업명: corp_code} 딕셔너리 반환."""
    global _corp_code_cache
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
    return mapping


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
