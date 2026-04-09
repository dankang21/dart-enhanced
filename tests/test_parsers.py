"""dart_enhanced.parsers 테스트."""

from dart_enhanced.client import FinancialItem
from dart_enhanced.parsers import parse_financial_statements, financials_to_dict


def _item(name: str, current: int, previous: int = 0, sj_div: str = "BS") -> FinancialItem:
    return FinancialItem(
        account_id="",
        account_name=name,
        current_amount=current,
        previous_amount=previous,
        before_previous_amount=0,
        statement_type=sj_div,
    )


class TestParseFinancialStatements:
    def test_balance_sheet(self):
        items = [
            _item("자산총계", 100_000),
            _item("부채총계", 40_000),
            _item("자본총계", 60_000),
            _item("유동자산", 30_000),
            _item("유동부채", 20_000),
        ]
        parsed = parse_financial_statements(items)
        assert parsed.total_assets == 100_000
        assert parsed.total_liabilities == 40_000
        assert parsed.total_equity == 60_000
        assert parsed.current_assets == 30_000
        assert parsed.current_liabilities == 20_000

    def test_income_statement(self):
        items = [
            _item("매출액", 50_000, previous=40_000, sj_div="IS"),
            _item("영업이익", 10_000, previous=8_000, sj_div="IS"),
            _item("당기순이익", 7_000, previous=5_000, sj_div="IS"),
        ]
        parsed = parse_financial_statements(items)
        assert parsed.revenue == 50_000
        assert parsed.operating_income == 10_000
        assert parsed.net_income == 7_000
        assert parsed.prev_revenue == 40_000

    def test_cash_flow(self):
        items = [
            _item("영업활동현금흐름", 15_000, sj_div="CF"),
            _item("투자활동현금흐름", -8_000, sj_div="CF"),
            _item("재무활동현금흐름", -3_000, sj_div="CF"),
        ]
        parsed = parse_financial_statements(items)
        assert parsed.operating_cash_flow == 15_000
        assert parsed.investing_cash_flow == -8_000
        assert parsed.fcf == 7_000  # 15000 + (-8000)

    def test_ratios(self):
        items = [
            _item("자산총계", 200_000),
            _item("부채총계", 80_000),
            _item("자본총계", 120_000),
            _item("유동자산", 50_000),
            _item("유동부채", 30_000),
            _item("매출액", 100_000, sj_div="IS"),
            _item("영업이익", 15_000, sj_div="IS"),
            _item("당기순이익", 10_000, sj_div="IS"),
        ]
        parsed = parse_financial_statements(items)

        assert parsed.debt_ratio is not None
        assert abs(parsed.debt_ratio - 80_000 / 120_000) < 1e-10

        assert parsed.roe is not None
        assert abs(parsed.roe - 10_000 / 120_000) < 1e-10

        assert parsed.operating_margin is not None
        assert abs(parsed.operating_margin - 0.15) < 1e-10

    def test_empty_input(self):
        parsed = parse_financial_statements([])
        assert parsed.total_assets == 0
        assert parsed.revenue == 0
        assert parsed.debt_ratio is None
        assert parsed.roe is None

    def test_revenue_growth(self):
        items = [
            _item("매출액", 120_000, previous=100_000, sj_div="IS"),
        ]
        parsed = parse_financial_statements(items)
        assert parsed.revenue_growth is not None
        assert abs(parsed.revenue_growth - 0.2) < 1e-10


class TestFinancialsToDict:
    def test_structure(self):
        items = [
            _item("자산총계", 100_000),
            _item("매출액", 50_000, sj_div="IS"),
            _item("당기순이익", 5_000, sj_div="IS"),
            _item("자본총계", 60_000),
        ]
        parsed = parse_financial_statements(items)
        d = financials_to_dict(parsed)

        assert "balance_sheet" in d
        assert "income_statement" in d
        assert "cash_flow" in d
        assert "ratios" in d
        assert "growth" in d
        assert d["balance_sheet"]["total_assets"] == 100_000
        assert d["income_statement"]["revenue"] == 50_000
