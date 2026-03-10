# Phase 0 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** "삼성전자 2025년 매출 알려줘" → DART Tool 호출 → LLM 요약 응답이 동작하는 End-to-End 시스템 구축

**Architecture:** FastMCP 서버(Streamable HTTP)가 DART/KRX Tool을 제공하고, Agent가 while+tool_use 루프로 Claude API와 MCP Tool을 연결. Docker Compose로 전체 기동.

**Tech Stack:** Python 3.12, MCP SDK (FastMCP + streamable-http), Anthropic SDK, FastAPI, FinanceDataReader, requests, pytest

---

### Task 1: Test infrastructure setup

**Files:**
- Create: `tests/conftest.py`
- Create: `tests/mcp_server/__init__.py`
- Create: `tests/agent/__init__.py`
- Create: `tests/__init__.py`
- Modify: `mcp_server/requirements.txt`
- Modify: `agent/requirements.txt`

**Step 1: Create test directory structure**

```bash
mkdir -p tests/mcp_server tests/agent
touch tests/__init__.py tests/mcp_server/__init__.py tests/agent/__init__.py
```

**Step 2: Create conftest.py with path setup**

Create `tests/conftest.py`:
```python
import sys
from pathlib import Path

# Add source directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "mcp_server"))
sys.path.insert(0, str(Path(__file__).parent.parent / "agent"))
```

**Step 3: Add test dependencies to mcp_server/requirements.txt**

Append to `mcp_server/requirements.txt`:
```
pytest>=8.0.0
pytest-asyncio>=0.24.0
```

**Step 4: Add test dependencies to agent/requirements.txt**

Append to `agent/requirements.txt`:
```
pytest>=8.0.0
pytest-asyncio>=0.24.0
httpx>=0.27.0
```

**Step 5: Verify test infrastructure runs**

```bash
cd /Users/idongju/Desktop/Git/fAInancial-agent
pip install pytest pytest-asyncio
python -m pytest tests/ -v --co
```
Expected: "no tests ran" (collected 0 items), no import errors.

**Step 6: Commit**

```bash
git add tests/ mcp_server/requirements.txt agent/requirements.txt
git commit -m "chore: add test infrastructure"
```

---

### Task 2: DART corp code resolver

**Files:**
- Create: `tests/mcp_server/test_dart_tools.py`
- Modify: `mcp_server/dart_tools.py`

**Step 1: Write failing test for corp code parsing**

Create `tests/mcp_server/test_dart_tools.py`:
```python
from unittest.mock import patch, MagicMock
import pytest

from dart_tools import resolve_corp_code


SAMPLE_CORP_XML = """<?xml version="1.0" encoding="UTF-8"?>
<result>
  <list>
    <corp_code>00126380</corp_code>
    <corp_name>삼성전자</corp_name>
    <stock_code>005930</stock_code>
    <modify_date>20231215</modify_date>
  </list>
  <list>
    <corp_code>00164779</corp_code>
    <corp_name>SK하이닉스</corp_name>
    <stock_code>000660</stock_code>
    <modify_date>20231215</modify_date>
  </list>
</result>"""


def test_resolve_corp_code_exact_match():
    with patch("dart_tools._load_corp_codes") as mock_load:
        mock_load.return_value = {
            "삼성전자": "00126380",
            "SK하이닉스": "00164779",
        }
        assert resolve_corp_code("삼성전자") == "00126380"


def test_resolve_corp_code_not_found():
    with patch("dart_tools._load_corp_codes") as mock_load:
        mock_load.return_value = {"삼성전자": "00126380"}
        with pytest.raises(ValueError, match="기업을 찾을 수 없습니다"):
            resolve_corp_code("없는회사")
```

**Step 2: Run test to verify it fails**

```bash
python -m pytest tests/mcp_server/test_dart_tools.py -v
```
Expected: FAIL — `ImportError: cannot import name 'resolve_corp_code'`

**Step 3: Implement corp code resolver**

Write `mcp_server/dart_tools.py`:
```python
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
```

**Step 4: Run test to verify it passes**

```bash
python -m pytest tests/mcp_server/test_dart_tools.py::test_resolve_corp_code_exact_match tests/mcp_server/test_dart_tools.py::test_resolve_corp_code_not_found -v
```
Expected: 2 passed

**Step 5: Commit**

```bash
git add tests/mcp_server/test_dart_tools.py mcp_server/dart_tools.py
git commit -m "feat: add DART corp code resolver with caching"
```

---

### Task 3: DART financial statements tool

**Files:**
- Modify: `tests/mcp_server/test_dart_tools.py`
- Modify: `mcp_server/dart_tools.py`

**Step 1: Write failing test for dart_financials**

Append to `tests/mcp_server/test_dart_tools.py`:
```python
from dart_tools import dart_financials

SAMPLE_FINANCIAL_RESPONSE = {
    "status": "000",
    "message": "정상",
    "list": [
        {
            "account_nm": "매출액",
            "thstrm_amount": "300,000,000,000",
            "frmtrm_amount": "250,000,000,000",
            "bfefrmtrm_amount": "200,000,000,000",
        },
        {
            "account_nm": "영업이익",
            "thstrm_amount": "50,000,000,000",
            "frmtrm_amount": "40,000,000,000",
            "bfefrmtrm_amount": "30,000,000,000",
        },
    ],
}


@patch("dart_tools.resolve_corp_code", return_value="00126380")
@patch("dart_tools.requests.get")
def test_dart_financials_success(mock_get, mock_resolve):
    mock_resp = MagicMock()
    mock_resp.json.return_value = SAMPLE_FINANCIAL_RESPONSE
    mock_resp.raise_for_status = MagicMock()
    mock_get.return_value = mock_resp

    result = dart_financials("삼성전자", "2024")
    assert "매출액" in result
    assert "300,000,000,000" in result
    mock_resolve.assert_called_once_with("삼성전자")


@patch("dart_tools.resolve_corp_code", return_value="00126380")
@patch("dart_tools.requests.get")
def test_dart_financials_api_error(mock_get, mock_resolve):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"status": "013", "message": "조회된 데이터가 없습니다."}
    mock_resp.raise_for_status = MagicMock()
    mock_get.return_value = mock_resp

    result = dart_financials("삼성전자", "2024")
    assert "조회된 데이터가 없습니다" in result
```

**Step 2: Run test to verify it fails**

```bash
python -m pytest tests/mcp_server/test_dart_tools.py::test_dart_financials_success -v
```
Expected: FAIL — `ImportError: cannot import name 'dart_financials'`

**Step 3: Implement dart_financials**

Append to `mcp_server/dart_tools.py`:
```python
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
```

**Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/mcp_server/test_dart_tools.py -v -k "dart_financials"
```
Expected: 2 passed

**Step 5: Commit**

```bash
git add tests/mcp_server/test_dart_tools.py mcp_server/dart_tools.py
git commit -m "feat: add DART financial statements tool"
```

---

### Task 4: DART disclosure search tool

**Files:**
- Modify: `tests/mcp_server/test_dart_tools.py`
- Modify: `mcp_server/dart_tools.py`

**Step 1: Write failing test for dart_search**

Append to `tests/mcp_server/test_dart_tools.py`:
```python
from dart_tools import dart_search

SAMPLE_SEARCH_RESPONSE = {
    "status": "000",
    "message": "정상",
    "total_count": 2,
    "list": [
        {
            "corp_name": "삼성전자",
            "report_nm": "사업보고서 (2024.12)",
            "rcept_dt": "20250401",
            "rcept_no": "20250401000123",
        },
        {
            "corp_name": "삼성전자",
            "report_nm": "분기보고서 (2025.03)",
            "rcept_dt": "20250515",
            "rcept_no": "20250515000456",
        },
    ],
}


@patch("dart_tools.requests.get")
def test_dart_search_success(mock_get):
    mock_resp = MagicMock()
    mock_resp.json.return_value = SAMPLE_SEARCH_RESPONSE
    mock_resp.raise_for_status = MagicMock()
    mock_get.return_value = mock_resp

    result = dart_search("삼성전자")
    assert "사업보고서" in result
    assert "2건" in result
```

**Step 2: Run test to verify it fails**

```bash
python -m pytest tests/mcp_server/test_dart_tools.py::test_dart_search_success -v
```
Expected: FAIL

**Step 3: Implement dart_search**

Append to `mcp_server/dart_tools.py`:
```python
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
```

**Step 4: Run test to verify it passes**

```bash
python -m pytest tests/mcp_server/test_dart_tools.py::test_dart_search_success -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add tests/mcp_server/test_dart_tools.py mcp_server/dart_tools.py
git commit -m "feat: add DART disclosure search tool"
```

---

### Task 5: KRX stock price tool

**Files:**
- Create: `tests/mcp_server/test_krx_tools.py`
- Modify: `mcp_server/krx_tools.py`

**Step 1: Write failing test for krx_price**

Create `tests/mcp_server/test_krx_tools.py`:
```python
from unittest.mock import patch, MagicMock
import pandas as pd

from krx_tools import krx_price


@patch("krx_tools.fdr.DataReader")
def test_krx_price_success(mock_reader):
    mock_df = pd.DataFrame(
        {
            "Open": [70000, 71000],
            "High": [72000, 73000],
            "Low": [69000, 70000],
            "Close": [71000, 72000],
            "Volume": [1000000, 1200000],
        },
        index=pd.to_datetime(["2025-01-02", "2025-01-03"]),
    )
    mock_reader.return_value = mock_df

    result = krx_price("005930", "2025-01-02", "2025-01-03")
    assert "005930" in result
    assert "71,000" in result or "71000" in result


@patch("krx_tools.fdr.DataReader")
def test_krx_price_empty(mock_reader):
    mock_reader.return_value = pd.DataFrame()

    result = krx_price("999999", "2025-01-02", "2025-01-03")
    assert "데이터가 없습니다" in result
```

**Step 2: Run test to verify it fails**

```bash
python -m pytest tests/mcp_server/test_krx_tools.py -v
```
Expected: FAIL

**Step 3: Implement krx_price**

Write `mcp_server/krx_tools.py`:
```python
"""
KRX 주가 Tool
주가 시세 조회 via FinanceDataReader
"""

import FinanceDataReader as fdr


def krx_price(ticker: str, start_date: str, end_date: str) -> str:
    """KRX 주가 데이터를 조회한다."""
    df = fdr.DataReader(ticker, start_date, end_date)

    if df.empty:
        return f"'{ticker}' 종목의 해당 기간 데이터가 없습니다"

    lines = [f"[{ticker}] 주가 ({start_date} ~ {end_date}), {len(df)}거래일"]
    lines.append(f"  시작가: {df['Close'].iloc[0]:,.0f}")
    lines.append(f"  종가:   {df['Close'].iloc[-1]:,.0f}")
    lines.append(f"  최고가: {df['High'].max():,.0f}")
    lines.append(f"  최저가: {df['Low'].min():,.0f}")
    lines.append(f"  평균거래량: {df['Volume'].mean():,.0f}")

    return "\n".join(lines)
```

**Step 4: Run tests to verify they pass**

```bash
pip install FinanceDataReader pandas
python -m pytest tests/mcp_server/test_krx_tools.py -v
```
Expected: 2 passed

**Step 5: Commit**

```bash
git add tests/mcp_server/test_krx_tools.py mcp_server/krx_tools.py
git commit -m "feat: add KRX stock price tool"
```

---

### Task 6: MCP Server with FastMCP (Streamable HTTP)

**Files:**
- Create: `tests/mcp_server/test_server.py`
- Modify: `mcp_server/main.py`
- Modify: `mcp_server/requirements.txt`

**Step 1: Write failing test for server tool registration**

Create `tests/mcp_server/test_server.py`:
```python
import pytest


def test_mcp_server_imports():
    """서버 모듈이 정상 임포트되고 tools가 등록되어 있는지 확인."""
    from main import mcp
    # FastMCP 인스턴스가 존재하는지 확인
    assert mcp.name == "fAInancial"
```

**Step 2: Run test to verify it fails**

```bash
python -m pytest tests/mcp_server/test_server.py -v
```
Expected: FAIL

**Step 3: Implement MCP server**

Write `mcp_server/main.py`:
```python
"""
fAInancial-agent MCP Server
DART 전자공시 + KRX 주가 데이터를 MCP Tool로 제공
Transport: Streamable HTTP
"""

from mcp.server.fastmcp import FastMCP

from dart_tools import dart_financials, dart_search
from krx_tools import krx_price

mcp = FastMCP("fAInancial", stateless_http=True)


@mcp.tool()
def get_financials(corp_name: str, year: str, report_type: str = "annual") -> str:
    """기업의 재무제표(매출액, 영업이익, 당기순이익 등)를 조회합니다.

    Args:
        corp_name: 기업명 (예: 삼성전자, SK하이닉스)
        year: 사업연도 (예: 2024)
        report_type: 보고서 유형 - annual(사업보고서), q1(1분기), half(반기), q3(3분기)
    """
    return dart_financials(corp_name, year, report_type)


@mcp.tool()
def search_disclosures(keyword: str) -> str:
    """DART 전자공시 시스템에서 공시를 검색합니다.

    Args:
        keyword: 검색 키워드 (기업명 또는 공시 관련 키워드)
    """
    return dart_search(keyword)


@mcp.tool()
def get_stock_price(ticker: str, start_date: str, end_date: str) -> str:
    """KRX 주가 데이터를 조회합니다.

    Args:
        ticker: 종목코드 (예: 005930)
        start_date: 조회 시작일 (YYYY-MM-DD)
        end_date: 조회 종료일 (YYYY-MM-DD)
    """
    return krx_price(ticker, start_date, end_date)


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8001)
```

**Step 4: Update mcp_server/requirements.txt**

```
mcp[cli]>=1.6.0
requests>=2.31.0
FinanceDataReader>=0.9.0
pytest>=8.0.0
pytest-asyncio>=0.24.0
```

**Step 5: Run test to verify it passes**

```bash
python -m pytest tests/mcp_server/test_server.py -v
```
Expected: PASS

**Step 6: Commit**

```bash
git add tests/mcp_server/test_server.py mcp_server/main.py mcp_server/requirements.txt
git commit -m "feat: add FastMCP server with streamable HTTP transport"
```

---

### Task 7: MCP Client (Streamable HTTP)

**Files:**
- Create: `tests/agent/test_mcp_client.py`
- Modify: `agent/mcp_client.py`

**Step 1: Write failing test for MCP client**

Create `tests/agent/test_mcp_client.py`:
```python
from unittest.mock import patch, MagicMock, AsyncMock
import pytest

from mcp_client import list_mcp_tools, call_mcp_tool, MCP_SERVER_URL


def test_mcp_server_url_default():
    assert "localhost" in MCP_SERVER_URL or "mcp-server" in MCP_SERVER_URL


@pytest.mark.asyncio
async def test_list_mcp_tools_returns_list():
    """list_mcp_tools가 Claude API 호환 형식의 tools 리스트를 반환하는지 확인."""
    mock_tool = MagicMock()
    mock_tool.name = "get_financials"
    mock_tool.description = "재무제표 조회"
    mock_tool.inputSchema = {
        "type": "object",
        "properties": {"corp_name": {"type": "string"}},
        "required": ["corp_name"],
    }

    mock_tools_result = MagicMock()
    mock_tools_result.tools = [mock_tool]

    mock_session = AsyncMock()
    mock_session.initialize = AsyncMock()
    mock_session.list_tools = AsyncMock(return_value=mock_tools_result)

    with patch("mcp_client.streamable_http_client") as mock_client, \
         patch("mcp_client.ClientSession") as mock_session_cls:
        mock_client.return_value.__aenter__ = AsyncMock(
            return_value=(MagicMock(), MagicMock(), MagicMock())
        )
        mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        tools = await list_mcp_tools()
        assert len(tools) == 1
        assert tools[0]["name"] == "get_financials"
        assert "input_schema" in tools[0]
```

**Step 2: Run test to verify it fails**

```bash
python -m pytest tests/agent/test_mcp_client.py -v
```
Expected: FAIL

**Step 3: Implement MCP client**

Write `agent/mcp_client.py`:
```python
"""
MCP Streamable HTTP 클라이언트
MCP 서버에서 Tool 목록 조회 + Tool 호출
"""

import os

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8001")


async def list_mcp_tools() -> list[dict]:
    """MCP 서버에서 Tool 목록을 조회하여 Claude API 호환 형식으로 반환."""
    async with streamable_http_client(f"{MCP_SERVER_URL}/mcp") as (
        read_stream,
        write_stream,
        _,
    ):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.list_tools()
            return [
                {
                    "name": tool.name,
                    "description": tool.description or "",
                    "input_schema": tool.inputSchema,
                }
                for tool in result.tools
            ]


async def call_mcp_tool(name: str, arguments: dict) -> str:
    """MCP 서버의 Tool을 호출하고 결과를 문자열로 반환."""
    async with streamable_http_client(f"{MCP_SERVER_URL}/mcp") as (
        read_stream,
        write_stream,
        _,
    ):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool(name, arguments)
            # content 블록들을 텍스트로 합침
            texts = []
            for block in result.content:
                if hasattr(block, "text"):
                    texts.append(block.text)
                else:
                    texts.append(str(block))
            return "\n".join(texts)
```

**Step 4: Run test to verify it passes**

```bash
python -m pytest tests/agent/test_mcp_client.py -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add tests/agent/test_mcp_client.py agent/mcp_client.py
git commit -m "feat: add MCP streamable HTTP client"
```

---

### Task 8: Agent Loop (while + tool_use)

**Files:**
- Create: `tests/agent/test_loop.py`
- Modify: `agent/loop.py`

**Step 1: Write failing test for agent loop — end_turn (no tool call)**

Create `tests/agent/test_loop.py`:
```python
from unittest.mock import patch, AsyncMock, MagicMock
import pytest

from loop import run_agent


def _make_text_block(text):
    block = MagicMock()
    block.type = "text"
    block.text = text
    return block


def _make_tool_block(tool_id, name, input_data):
    block = MagicMock()
    block.type = "tool_use"
    block.id = tool_id
    block.name = name
    block.input = input_data
    return block


@pytest.mark.asyncio
@patch("loop.call_mcp_tool", new_callable=AsyncMock)
@patch("loop.list_mcp_tools", new_callable=AsyncMock)
@patch("loop.client")
async def test_run_agent_simple_response(mock_client, mock_list_tools, mock_call_tool):
    """tool_use 없이 바로 end_turn하는 케이스."""
    mock_list_tools.return_value = []

    mock_response = MagicMock()
    mock_response.stop_reason = "end_turn"
    mock_response.content = [_make_text_block("안녕하세요!")]
    mock_client.messages.create = MagicMock(return_value=mock_response)

    result = await run_agent("안녕")
    assert result == "안녕하세요!"


@pytest.mark.asyncio
@patch("loop.call_mcp_tool", new_callable=AsyncMock)
@patch("loop.list_mcp_tools", new_callable=AsyncMock)
@patch("loop.client")
async def test_run_agent_with_tool_call(mock_client, mock_list_tools, mock_call_tool):
    """tool_use → tool_result → end_turn 흐름 테스트."""
    mock_list_tools.return_value = [
        {"name": "get_financials", "description": "재무제표", "input_schema": {}}
    ]
    mock_call_tool.return_value = "삼성전자 매출: 300조"

    # 첫 번째 호출: tool_use 응답
    tool_response = MagicMock()
    tool_response.stop_reason = "tool_use"
    tool_response.content = [
        _make_tool_block("tool_1", "get_financials", {"corp_name": "삼성전자", "year": "2024"})
    ]

    # 두 번째 호출: end_turn 응답
    final_response = MagicMock()
    final_response.stop_reason = "end_turn"
    final_response.content = [_make_text_block("삼성전자의 2024년 매출은 300조원입니다.")]

    mock_client.messages.create = MagicMock(side_effect=[tool_response, final_response])

    result = await run_agent("삼성전자 매출 알려줘")
    assert "300조" in result
    mock_call_tool.assert_called_once_with("get_financials", {"corp_name": "삼성전자", "year": "2024"})
```

**Step 2: Run test to verify it fails**

```bash
python -m pytest tests/agent/test_loop.py -v
```
Expected: FAIL

**Step 3: Implement agent loop**

Write `agent/loop.py`:
```python
"""
Agent Loop — 프레임워크 없이 직접 구현
패턴: while stop_reason != "end_turn": tool_use → MCP 호출 → tool_result 주입
"""

import os

import anthropic

from mcp_client import call_mcp_tool, list_mcp_tools

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))

SYSTEM_PROMPT = (
    "당신은 한국 금융 데이터 분석 AI 어시스턴트입니다. "
    "DART 전자공시와 KRX 주가 데이터를 조회하는 도구를 사용하여 "
    "사용자의 질문에 정확하게 답변하세요. "
    "데이터를 조회한 후에는 핵심 수치를 포함하여 명확하게 요약해주세요."
)

MAX_ITERATIONS = 10


async def run_agent(user_message: str) -> str:
    """Agent Loop: Claude API + MCP Tool 연동."""
    tools = await list_mcp_tools()
    messages = [{"role": "user", "content": user_message}]

    for _ in range(MAX_ITERATIONS):
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=tools,
            messages=messages,
        )

        if response.stop_reason == "end_turn":
            # 마지막 text 블록 반환
            for block in reversed(response.content):
                if block.type == "text":
                    return block.text
            return ""

        # tool_use 처리
        messages.append({"role": "assistant", "content": response.content})
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                result = await call_mcp_tool(block.name, block.input)
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    }
                )
        messages.append({"role": "user", "content": tool_results})

    return "최대 반복 횟수에 도달했습니다. 다시 시도해주세요."
```

**Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/agent/test_loop.py -v
```
Expected: 2 passed

**Step 5: Commit**

```bash
git add tests/agent/test_loop.py agent/loop.py
git commit -m "feat: add agent loop with while + tool_use pattern"
```

---

### Task 9: FastAPI endpoint

**Files:**
- Create: `tests/agent/test_main.py`
- Modify: `agent/main.py`

**Step 1: Write failing test for POST /chat**

Create `tests/agent/test_main.py`:
```python
from unittest.mock import patch, AsyncMock
import pytest
from httpx import AsyncClient, ASGITransport

from main import app


@pytest.mark.asyncio
@patch("main.run_agent", new_callable=AsyncMock)
async def test_chat_endpoint(mock_run_agent):
    mock_run_agent.return_value = "삼성전자의 2024년 매출은 300조원입니다."

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/chat", json={"message": "삼성전자 매출"})

    assert resp.status_code == 200
    data = resp.json()
    assert "300조" in data["response"]


@pytest.mark.asyncio
async def test_health_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")

    assert resp.status_code == 200
```

**Step 2: Run test to verify it fails**

```bash
python -m pytest tests/agent/test_main.py -v
```
Expected: FAIL

**Step 3: Implement FastAPI app**

Write `agent/main.py`:
```python
"""
fAInancial-agent FastAPI 진입점
POST /chat → Agent Loop 실행
"""

from fastapi import FastAPI
from pydantic import BaseModel

from loop import run_agent

app = FastAPI(title="fAInancial-agent")


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    result = await run_agent(req.message)
    return ChatResponse(response=result)


@app.get("/health")
async def health():
    return {"status": "ok"}
```

**Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/agent/test_main.py -v
```
Expected: 2 passed

**Step 5: Commit**

```bash
git add tests/agent/test_main.py agent/main.py
git commit -m "feat: add FastAPI /chat endpoint"
```

---

### Task 10: Docker Compose & requirements update

**Files:**
- Modify: `docker-compose.yml`
- Modify: `agent/requirements.txt`
- Modify: `mcp_server/requirements.txt`

**Step 1: Update docker-compose.yml — MCP_SERVER_URL에 /mcp 경로 추가**

`docker-compose.yml` 의 `MCP_SERVER_URL` 값을 변경:
```yaml
environment:
  - MCP_SERVER_URL=http://mcp-server:8001
```
→ Streamable HTTP는 `/mcp` 경로가 기본이므로 MCP client 코드에서 이미 `/mcp`를 append함. docker-compose.yml은 변경 불필요.

**Step 2: Finalize mcp_server/requirements.txt**

```
mcp[cli]>=1.6.0
requests>=2.31.0
FinanceDataReader>=0.9.0
```

**Step 3: Finalize agent/requirements.txt**

```
anthropic>=0.40.0
mcp>=1.6.0
fastapi>=0.115.0
uvicorn>=0.32.0
pydantic>=2.0.0
```

**Step 4: Run all tests**

```bash
python -m pytest tests/ -v
```
Expected: All tests pass

**Step 5: Commit**

```bash
git add docker-compose.yml agent/requirements.txt mcp_server/requirements.txt
git commit -m "chore: finalize dependencies for Phase 0"
```

---

### Task 11: End-to-End smoke test (manual)

**Files:**
- None (manual verification)

**Step 1: .env 파일 존재 확인**

```bash
# Human이 .env 파일에 ANTHROPIC_API_KEY, DART_API_KEY를 설정해야 함
ls -la .env
```

**Step 2: Docker Compose 빌드 및 실행**

```bash
docker compose build
docker compose up -d
```
Expected: 두 서비스 모두 healthy 상태

**Step 3: Health check**

```bash
curl http://localhost:8000/health
```
Expected: `{"status": "ok"}`

**Step 4: E2E 테스트 — 재무제표 조회**

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "삼성전자 2024년 매출 알려줘"}'
```
Expected: DART에서 재무제표를 조회하여 매출액을 포함한 LLM 요약 응답

**Step 5: Docker Compose 정리**

```bash
docker compose down
```

**Step 6: Commit (if any fixes were needed)**

```bash
git add -A
git commit -m "fix: E2E test adjustments"
```
