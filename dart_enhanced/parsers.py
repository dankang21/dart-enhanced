"""DART financial statement parsing module.

Converts raw financial statement data into a structured format
suitable for analysis.
"""

from dataclasses import dataclass

from .client import FinancialItem


@dataclass
class ParsedFinancials:
    """Parsed core financial data."""

    # Balance Sheet (재무상태표)
    total_assets: int = 0
    total_liabilities: int = 0
    total_equity: int = 0
    current_assets: int = 0
    current_liabilities: int = 0

    # Income Statement (손익계산서)
    revenue: int = 0
    operating_income: int = 0
    net_income: int = 0

    # Cash Flow Statement (현금흐름표)
    operating_cash_flow: int = 0
    investing_cash_flow: int = 0
    financing_cash_flow: int = 0

    # Prior period data (전기 데이터)
    prev_revenue: int = 0
    prev_operating_income: int = 0
    prev_net_income: int = 0
    prev_total_assets: int = 0
    prev_total_equity: int = 0

    @property
    def fcf(self) -> int:
        """Free Cash Flow (잉여현금흐름) = Operating CF + Investing CF."""
        return self.operating_cash_flow + self.investing_cash_flow

    @property
    def debt_ratio(self) -> float | None:
        """Debt-to-Equity Ratio (부채비율)."""
        if self.total_equity <= 0:
            return None
        return self.total_liabilities / self.total_equity

    @property
    def current_ratio(self) -> float | None:
        """Current Ratio (유동비율)."""
        if self.current_liabilities <= 0:
            return None
        return self.current_assets / self.current_liabilities

    @property
    def operating_margin(self) -> float | None:
        """Operating Profit Margin (영업이익률)."""
        if self.revenue <= 0:
            return None
        return self.operating_income / self.revenue

    @property
    def net_margin(self) -> float | None:
        """Net Profit Margin (순이익률)."""
        if self.revenue <= 0:
            return None
        return self.net_income / self.revenue

    @property
    def roe(self) -> float | None:
        """Return on Equity (자기자본이익률)."""
        if self.total_equity <= 0:
            return None
        return self.net_income / self.total_equity

    @property
    def roa(self) -> float | None:
        """Return on Assets (총자산이익률)."""
        if self.total_assets <= 0:
            return None
        return self.net_income / self.total_assets

    @property
    def revenue_growth(self) -> float | None:
        """Revenue growth rate vs. prior period (매출 성장률, 전기 대비)."""
        if self.prev_revenue <= 0:
            return None
        return (self.revenue - self.prev_revenue) / self.prev_revenue

    @property
    def net_income_growth(self) -> float | None:
        """Net income growth rate (순이익 성장률)."""
        if self.prev_net_income <= 0:
            return None
        return (self.net_income - self.prev_net_income) / self.prev_net_income


# Account name matching keywords.
# DART account names vary slightly across companies, so we match by keyword.
_ACCOUNT_PATTERNS = {
    "total_assets": ["자산총계"],
    "total_liabilities": ["부채총계"],
    "total_equity": ["자본총계"],
    "current_assets": ["유동자산"],
    "current_liabilities": ["유동부채"],
    "revenue": ["매출액", "수익(매출액)", "영업수익"],
    "operating_income": ["영업이익", "영업이익(손실)"],
    "net_income": ["당기순이익", "당기순이익(손실)"],
    "operating_cash_flow": ["영업활동현금흐름", "영업활동으로인한현금흐름"],
    "investing_cash_flow": ["투자활동현금흐름", "투자활동으로인한현금흐름"],
    "financing_cash_flow": ["재무활동현금흐름", "재무활동으로인한현금흐름"],
}


def parse_financial_statements(items: list[FinancialItem]) -> ParsedFinancials:
    """Parse a list of financial statement items into core financial data.

    Args:
        items: Result from DartClient.get_financial_statements().

    Returns:
        A ParsedFinancials instance.
    """
    result = ParsedFinancials()

    # Multiple items may match the same field; prefer the first non-zero value.
    matched: set[str] = set()

    for item in items:
        name = item.account_name.strip()

        for field, patterns in _ACCOUNT_PATTERNS.items():
            if name in patterns:
                # Skip if a non-zero value has already been set for this field.
                if field in matched and getattr(result, field) != 0:
                    break

                if item.current_amount != 0:
                    setattr(result, field, item.current_amount)
                    matched.add(field)

                    if field == "revenue":
                        result.prev_revenue = item.previous_amount
                    elif field == "operating_income":
                        result.prev_operating_income = item.previous_amount
                    elif field == "net_income":
                        result.prev_net_income = item.previous_amount
                    elif field == "total_assets":
                        result.prev_total_assets = item.previous_amount
                    elif field == "total_equity":
                        result.prev_total_equity = item.previous_amount
                break

    return result


def financials_to_dict(parsed: ParsedFinancials) -> dict:
    """Convert parsed financial data to a dictionary (for API responses)."""
    return {
        "balance_sheet": {
            "total_assets": parsed.total_assets,
            "total_liabilities": parsed.total_liabilities,
            "total_equity": parsed.total_equity,
            "current_assets": parsed.current_assets,
            "current_liabilities": parsed.current_liabilities,
        },
        "income_statement": {
            "revenue": parsed.revenue,
            "operating_income": parsed.operating_income,
            "net_income": parsed.net_income,
        },
        "cash_flow": {
            "operating": parsed.operating_cash_flow,
            "investing": parsed.investing_cash_flow,
            "financing": parsed.financing_cash_flow,
            "fcf": parsed.fcf,
        },
        "ratios": {
            "debt_ratio": _round_or_none(parsed.debt_ratio, 4),
            "current_ratio": _round_or_none(parsed.current_ratio, 4),
            "operating_margin": _round_or_none(parsed.operating_margin, 4),
            "net_margin": _round_or_none(parsed.net_margin, 4),
            "roe": _round_or_none(parsed.roe, 4),
            "roa": _round_or_none(parsed.roa, 4),
        },
        "growth": {
            "revenue_growth": _round_or_none(parsed.revenue_growth, 4),
            "net_income_growth": _round_or_none(parsed.net_income_growth, 4),
        },
    }


def _round_or_none(value: float | None, decimals: int) -> float | None:
    if value is None:
        return None
    return round(value, decimals)
