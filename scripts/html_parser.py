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

    # 블록 요소 뒤에만 개행 삽입 (인라인 태그는 공백 유지)
    block_tags = ["p", "div", "br", "h1", "h2", "h3", "h4", "h5", "h6", "li", "tr", "td"]
    for tag in soup.find_all(block_tags):
        tag.append("\n")

    text = soup.get_text(separator="")

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)
