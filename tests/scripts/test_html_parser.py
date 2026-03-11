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
