"""DART OpenAPI client.

Retrieves company information, financial statements, and disclosures
via the DART (Data Analysis, Retrieval and Transfer System, 전자공시시스템) OpenAPI.
API docs: https://opendart.fss.or.kr/guide/main.do
"""

import io
import os
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Any

import httpx


BASE_URL = "https://opendart.fss.or.kr/api"

# Report codes (보고서 코드)
REPORT_CODES = {
    "annual": "11011",      # Annual report (사업보고서)
    "half": "11012",        # Semi-annual report (반기보고서)
    "q1": "11013",          # Q1 report (1분기보고서)
    "q3": "11014",          # Q3 report (3분기보고서)
}


@dataclass
class CompanyInfo:
    """Company overview (기업 개황)."""
    corp_code: str
    corp_name: str
    stock_code: str | None
    stock_name: str | None
    ceo: str
    corp_cls: str  # Y=KOSPI (유가), K=KOSDAQ (코스닥), N=KONEX (코넥스), E=Others (기타)
    address: str
    website: str
    industry_code: str
    established: str  # YYYYMMDD
    fiscal_month: str  # Fiscal year-end month (결산월)


@dataclass
class FinancialItem:
    """Financial statement line item (재무제표 항목)."""
    account_id: str      # Account ID (계정 ID)
    account_name: str    # Account name (계정명)
    current_amount: int  # Current period amount (당기 금액)
    previous_amount: int # Prior period amount (전기 금액)
    before_previous_amount: int  # Two periods ago amount (전전기 금액)
    statement_type: str  # BS=Balance Sheet (재무상태표), IS=Income Statement (손익계산서), CF=Cash Flow Statement (현금흐름표), etc.


class DartClient:
    """Async client for the DART OpenAPI (DART OpenAPI 비동기 클라이언트)."""

    def __init__(
        self,
        api_key: str | None = None,
    ):
        self.api_key = api_key or os.environ.get("DART_API_KEY", "")
        if not self.api_key:
            raise ValueError(
                "DART API key is required. Set the DART_API_KEY environment variable "
                "or pass it to the constructor."
            )

        self._client = httpx.AsyncClient(timeout=30.0)
        self._corp_code_cache: dict[str, str] | None = None

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()

    async def _request(self, endpoint: str, params: dict | None = None) -> dict:
        """Send a request to the DART API."""
        url = f"{BASE_URL}/{endpoint}"
        req_params = {"crtfc_key": self.api_key}
        if params:
            req_params.update(params)

        resp = await self._client.get(url, params=req_params)
        resp.raise_for_status()

        data = resp.json()
        status = data.get("status", "")

        if status == "013":
            raise DartApiError("No data found.", status)
        elif status not in ("000", ""):
            raise DartApiError(
                f"DART API error: {data.get('message', 'Unknown')} (status={status})",
                status,
            )

        return data

    # -- Corporation codes (기업 코드) --

    async def load_corp_codes(self) -> dict[str, str]:
        """Load the full list of corporation codes (stock_code -> corp_code mapping).

        Returns:
            A dict mapping {stock_code: corp_code} for listed companies only.
        """
        if self._corp_code_cache is not None:
            return self._corp_code_cache

        url = f"{BASE_URL}/corpCode.xml"
        resp = await self._client.get(
            url, params={"crtfc_key": self.api_key}, timeout=60.0
        )
        resp.raise_for_status()

        zf = zipfile.ZipFile(io.BytesIO(resp.content))
        xml_content = zf.read("CORPCODE.xml")
        root = ET.fromstring(xml_content)

        mapping = {}
        for item in root.findall("list"):
            stock_code = item.findtext("stock_code", "").strip()
            corp_code = item.findtext("corp_code", "").strip()
            if stock_code:  # Listed companies only (상장 기업만)
                mapping[stock_code] = corp_code

        self._corp_code_cache = mapping
        return mapping

    async def get_corp_code(self, stock_code: str) -> str:
        """Look up a DART corp_code by stock code (6-digit)."""
        codes = await self.load_corp_codes()
        if stock_code not in codes:
            raise ValueError(f"Stock code '{stock_code}' not found.")
        return codes[stock_code]

    # -- Company overview (기업 개황) --

    async def get_company_info(self, corp_code: str) -> CompanyInfo:
        """Retrieve company overview information.

        Args:
            corp_code: DART corporation unique code (8-digit).
        """
        data = await self._request("company.json", {"corp_code": corp_code})

        return CompanyInfo(
            corp_code=data["corp_code"],
            corp_name=data.get("corp_name", ""),
            stock_code=data.get("stock_code") or None,
            stock_name=data.get("stock_name") or None,
            ceo=data.get("ceo_nm", ""),
            corp_cls=data.get("corp_cls", ""),
            address=data.get("adres", ""),
            website=data.get("hm_url", ""),
            industry_code=data.get("induty_code", ""),
            established=data.get("est_dt", ""),
            fiscal_month=data.get("acc_mt", ""),
        )

    async def get_company_info_by_stock(self, stock_code: str) -> CompanyInfo:
        """Retrieve company overview by stock code."""
        corp_code = await self.get_corp_code(stock_code)
        return await self.get_company_info(corp_code)

    # -- Financial statements (재무제표) --

    async def get_financial_statements(
        self,
        corp_code: str,
        year: int,
        report_type: str = "annual",
        consolidated: bool = True,
    ) -> list[FinancialItem]:
        """Retrieve financial statements.

        Args:
            corp_code: DART corporation code.
            year: Business year.
            report_type: One of "annual", "half", "q1", "q3".
            consolidated: True for consolidated (연결), False for separate (별도).

        Returns:
            A list of FinancialItem objects.
        """
        reprt_code = REPORT_CODES.get(report_type)
        if not reprt_code:
            raise ValueError(f"Unsupported report type: {report_type}")

        data = await self._request(
            "fnlttSinglAcntAll.json",
            {
                "corp_code": corp_code,
                "bsns_year": str(year),
                "reprt_code": reprt_code,
                "fs_div": "CFS" if consolidated else "OFS",
            },
        )

        items = []
        for row in data.get("list", []):
            items.append(
                FinancialItem(
                    account_id=row.get("account_id", ""),
                    account_name=row.get("account_nm", ""),
                    current_amount=_parse_amount(row.get("thstrm_amount")),
                    previous_amount=_parse_amount(row.get("frmtrm_amount")),
                    before_previous_amount=_parse_amount(
                        row.get("bfefrmtrm_amount")
                    ),
                    statement_type=_classify_statement(row.get("sj_div", "")),
                )
            )
        return items

    async def get_financial_statements_by_stock(
        self,
        stock_code: str,
        year: int,
        report_type: str = "annual",
        consolidated: bool = True,
    ) -> list[FinancialItem]:
        """Retrieve financial statements by stock code."""
        corp_code = await self.get_corp_code(stock_code)
        return await self.get_financial_statements(
            corp_code, year, report_type, consolidated
        )

    # -- Disclosure search (공시 검색) --

    async def search_disclosures(
        self,
        corp_code: str | None = None,
        begin_date: str | None = None,
        end_date: str | None = None,
        page_no: int = 1,
        page_count: int = 100,
    ) -> dict[str, Any]:
        """Search disclosures (공시).

        Args:
            corp_code: Corporation code (None for all).
            begin_date: Search start date (YYYYMMDD).
            end_date: Search end date (YYYYMMDD).
            page_no: Page number.
            page_count: Items per page (max 100).

        Returns:
            {"total_count": int, "page_no": int, "items": list[dict]}
        """
        params: dict[str, Any] = {
            "page_no": str(page_no),
            "page_count": str(page_count),
        }
        if corp_code:
            params["corp_code"] = corp_code
        if begin_date:
            params["bgn_de"] = begin_date
        if end_date:
            params["end_de"] = end_date

        data = await self._request("list.json", params)

        items = []
        for row in data.get("list", []):
            items.append({
                "corp_code": row.get("corp_code", ""),
                "corp_name": row.get("corp_name", ""),
                "report_name": row.get("report_nm", ""),
                "receipt_no": row.get("rcept_no", ""),
                "flr_name": row.get("flr_nm", ""),  # Disclosure filer (공시 제출인)
                "receipt_date": row.get("rcept_dt", ""),
                "remarks": row.get("rm", ""),
            })

        return {
            "total_count": int(data.get("total_count", 0)),
            "page_no": int(data.get("page_no", 1)),
            "items": items,
        }

    # -- Dividends (배당) --

    async def get_dividend_info(
        self, corp_code: str, year: int, report_type: str = "annual"
    ) -> list[dict]:
        """Retrieve dividend-related information."""
        reprt_code = REPORT_CODES.get(report_type, "11011")
        data = await self._request(
            "alotMatter.json",
            {
                "corp_code": corp_code,
                "bsns_year": str(year),
                "reprt_code": reprt_code,
            },
        )
        return data.get("list", [])


# -- Utilities --

def _parse_amount(value: str | None) -> int:
    """Convert an amount string to an integer."""
    if not value:
        return 0
    try:
        return int(value.replace(",", "").replace(" ", ""))
    except (ValueError, TypeError):
        return 0


def _classify_statement(sj_div: str) -> str:
    """Classify a financial statement division code."""
    mapping = {
        "BS": "BS",   # Balance Sheet (재무상태표)
        "IS": "IS",   # Income Statement (손익계산서)
        "CIS": "IS",  # Comprehensive Income Statement (포괄손익계산서)
        "CF": "CF",   # Cash Flow Statement (현금흐름표)
        "SCE": "SCE", # Statement of Changes in Equity (자본변동표)
    }
    return mapping.get(sj_div, sj_div)


class DartApiError(Exception):
    """DART API error."""

    def __init__(self, message: str, status_code: str = ""):
        super().__init__(message)
        self.status_code = status_code
