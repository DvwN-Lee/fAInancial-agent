from scripts.index_documents import _is_boilerplate


def test_cover_page_is_boilerplate():
    """DART 보고서 표지는 보일러플레이트로 판별된다."""
    cover = (
        "사업보고서\n5.5\n삼성전자주식회사\nC\nA\nY\n130111-0006246\n"
        "사 업 보 고 서\n(제 55 기)\n사업연도\n2023년 01월 01일\n부터\n"
        "2023년 12월 31일\n까지\n금융위원회\n한국거래소 귀중\n"
        "제출대상법인 유형 :\n주권상장법인\n면제사유발생 :\n해당사항 없음"
    )
    assert _is_boilerplate(cover) is True


def test_toc_is_boilerplate():
    """목차 + 대표이사 확인서 마커가 있으면 보일러플레이트."""
    toc = (
        "【 대표이사 등의 확인 】\n"
        "I. 회사의 개요\n"
        "II. 사업의 내용\n"
        "금융위원회\n한국거래소 귀중"
    )
    assert _is_boilerplate(toc) is True


def test_real_content_not_boilerplate():
    """실제 사업 내용 텍스트는 보일러플레이트가 아니다."""
    content = (
        "당사는 TV, 냉장고, 세탁기, 에어컨, 스마트폰 등 완제품과 "
        "DRAM, NAND Flash, 모바일AP 등 반도체 부품 및 스마트폰용 "
        "OLED 패널 등을 생산·판매하고 있습니다. 아울러 Harman을 통해 "
        "디지털 콕핏, 카오디오 등을 생산·판매하고 있습니다."
    )
    assert _is_boilerplate(content) is False


def test_short_text_is_boilerplate():
    """50자 미만 짧은 텍스트는 보일러플레이트."""
    assert _is_boilerplate("가나다") is True
    assert _is_boilerplate("") is True


def test_single_marker_not_boilerplate():
    """마커가 1개만 있으면 보일러플레이트가 아니다 (본문에 언급 가능)."""
    text = (
        "금융위원회의 규정에 따라 사업보고서를 제출합니다. "
        "당사의 주요 사업 현황과 재무제표를 아래와 같이 보고합니다. "
        "반도체 사업부문의 매출은 전년 대비 증가하였습니다."
    )
    assert _is_boilerplate(text) is False


def test_subsidiary_table_is_boilerplate():
    """자회사 소유지분 테이블은 보일러플레이트로 판별된다."""
    table = "\n".join([
        "삼성전자(주)",
        "Samsung Electronics Italia S.P.A.",
        "100.0",
        "삼성전자(주)",
        "Samsung Electronics Iberia, S.A.",
        "100.0",
        "삼성전자(주)",
        "Samsung Electronics (UK) Ltd.",
        "100.0",
        "삼성전자(주)",
        "Samsung Electronics Canada, Inc.",
        "100.0",
    ])
    assert _is_boilerplate(table) is True


def test_narrative_with_linebreaks_not_boilerplate():
    """줄바꿈이 있어도 서술형 텍스트는 보일러플레이트가 아니다."""
    text = (
        "당사는 영업활동에서 파생되는 시장위험, 신용위험, 유동성위험 등을 "
        "최소화하는데 중점을 두고 재무위험을 관리하고 있습니다.\n"
        "당사 재무위험관리의 주요 대상인 자산은 현금및현금성자산, 단기금융상품, "
        "상각후원가금융자산, 매출채권 등으로 구성되어 있습니다.\n"
        "부채는 매입채무, 차입금 등으로 구성되어 있습니다."
    )
    assert _is_boilerplate(text) is False


def test_corp_name_list_is_boilerplate():
    """법인명 접미사가 5개 이상이면 자회사 목록으로 판별된다."""
    text = (
        "Samsung Electronics Italia S.P.A.\n"
        "Samsung Electronics Iberia, S.A.\n"
        "Samsung (CHINA) Investment Co., Ltd. (SCIC)\n"
        "Samsung Semiconductor, Inc. (SSI)\n"
        "Samsung Display Vietnam Co., Ltd. (SDV)\n"
        "Samsung Eletronica da Amazonia Ltda. (SEDA)\n"
        "Samsung Electronics GmbH (SEG)"
    )
    assert _is_boilerplate(text) is True


def test_few_corp_names_not_boilerplate():
    """법인명 접미사가 4개 이하면 본문 언급으로 허용된다."""
    text = (
        "당사의 주요 종속기업으로는 Samsung Semiconductor, Inc.와 "
        "Samsung Display Co., Ltd.가 있으며, 이들 법인은 반도체 및 "
        "디스플레이 사업을 영위하고 있습니다. 또한 Samsung Electronics "
        "America, Inc.를 통해 북미 시장을 공략하고 있습니다."
    )
    assert _is_boilerplate(text) is False
