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
