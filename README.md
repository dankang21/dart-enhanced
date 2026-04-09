# dart-enhanced

**Async Python client for Korea's DART (FSS) OpenAPI**

An async Python client for the DART (Electronic Disclosure System) OpenAPI. Supports financial statement parsing, company overview, disclosure search, and dividend lookup.

[![PyPI](https://img.shields.io/pypi/v/dart-enhanced)](https://pypi.org/project/dart-enhanced/)
[![Python](https://img.shields.io/pypi/pyversions/dart-enhanced)](https://pypi.org/project/dart-enhanced/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-20%20passed-brightgreen)]()

## Features

- **Async-first** — Async HTTP client built on `httpx`
- **Zero pandas dependency** — Pure Python dataclasses, no numpy required
- **Financial statement parser** — Converts raw financial data into structured `ParsedFinancials`
- **Auto ratios** — Automatically calculates ROE, ROA, debt ratio, operating margin, FCF, and more
- **Fully typed** — `py.typed` marker with type hints on all public APIs
- **Corp code cache** — In-memory caching of corp code mappings to avoid redundant lookups

## Installation

```bash
pip install dart-enhanced
```

## Quick Start

```python
import asyncio
from dart_enhanced import DartClient, DartApiError, parse_financial_statements, financials_to_dict

async def main():
    async with DartClient(api_key="YOUR_DART_API_KEY") as client:
        # Company overview for Samsung Electronics
        info = await client.get_company_info_by_stock("005930")
        print(f"{info.corp_name} ({info.ceo})")
        # → Samsung Electronics (Jong-Hee Han)

        # Fetch and parse financial statements
        items = await client.get_financial_statements_by_stock(
            "005930", year=2024, report_type="annual"
        )
        parsed = parse_financial_statements(items)
        print(f"Revenue: {parsed.revenue:,} KRW")
        print(f"ROE: {parsed.roe:.2%}")
        print(f"Debt ratio: {parsed.debt_ratio:.2%}")

        # Convert to dict for API responses
        data = financials_to_dict(parsed)
        print(data["ratios"])

asyncio.run(main())
```

### Error Handling

```python
from dart_enhanced import DartClient, DartApiError

async with DartClient() as client:
    try:
        info = await client.get_company_info_by_stock("999999")
    except ValueError as e:
        print(f"Stock code not found: {e}")
    except DartApiError as e:
        print(f"DART API error: {e} (status={e.status_code})")
```

`DartApiError.status_code` contains the DART API error code:
- `"013"` — No data found
- `"020"` — Request limit exceeded
- `"800"` — System maintenance in progress

## API Reference

### DartClient

```python
client = DartClient(api_key="...")  # or use env var DART_API_KEY
```

| Method | Description |
|--------|-------------|
| `load_corp_codes()` | Load full corp code mapping (stock code → corp_code) |
| `get_corp_code(stock_code)` | Look up DART corp_code (8 digits) by stock code (6 digits) |
| `get_company_info(corp_code)` | Get company overview → `CompanyInfo` |
| `get_company_info_by_stock(stock_code)` | Get company overview by stock code |
| `get_financial_statements(corp_code, year, report_type, consolidated)` | Get financial statements → `list[FinancialItem]` |
| `get_financial_statements_by_stock(stock_code, ...)` | Get financial statements by stock code |
| `search_disclosures(corp_code, begin_date, end_date, ...)` | Search disclosures |
| `get_dividend_info(corp_code, year, report_type)` | Get dividend information |
| `close()` | Close the HTTP client (called automatically when using context manager) |

> **Stock code vs corp_code**: DART uses its own corporate code (`corp_code`, 8 digits), which differs from the stock exchange ticker (e.g., `005930`). The `_by_stock` methods handle the stock code → corp_code conversion automatically.

### CompanyInfo

Return type for `get_company_info()`:

| Field | Type | Description |
|-------|------|-------------|
| `corp_code` | `str` | DART unique corporate code (8 digits) |
| `corp_name` | `str` | Company name |
| `stock_code` | `str \| None` | Stock code (None if unlisted) |
| `stock_name` | `str \| None` | Stock name |
| `ceo` | `str` | CEO |
| `corp_cls` | `str` | Y=KOSPI, K=KOSDAQ, N=KONEX, E=Other |
| `address` | `str` | Headquarters address |
| `website` | `str` | Website URL |
| `industry_code` | `str` | Industry code |
| `established` | `str` | Date of establishment (YYYYMMDD) |
| `fiscal_month` | `str` | Fiscal year-end month |

### FinancialItem

Return type for `get_financial_statements()` (list):

| Field | Type | Description |
|-------|------|-------------|
| `account_id` | `str` | Account ID |
| `account_name` | `str` | Account name (e.g., "Revenue", "Total Assets") |
| `current_amount` | `int` | Current period amount |
| `previous_amount` | `int` | Previous period amount |
| `before_previous_amount` | `int` | Period before previous amount |
| `statement_type` | `str` | BS=Balance Sheet, IS=Income Statement, CF=Cash Flow Statement, SCE=Statement of Changes in Equity |

### Financial Statement Parser

```python
from dart_enhanced import parse_financial_statements, financials_to_dict, ParsedFinancials

parsed = parse_financial_statements(items)  # → ParsedFinancials
```

**Balance Sheet (BS)**

| Property | Type | Description |
|----------|------|-------------|
| `total_assets` | `int` | Total assets |
| `total_liabilities` | `int` | Total liabilities |
| `total_equity` | `int` | Total equity |
| `current_assets` | `int` | Current assets |
| `current_liabilities` | `int` | Current liabilities |

**Income Statement (IS)**

| Property | Type | Description |
|----------|------|-------------|
| `revenue` | `int` | Revenue |
| `operating_income` | `int` | Operating income |
| `net_income` | `int` | Net income |

**Cash Flow Statement (CF)**

| Property | Type | Description |
|----------|------|-------------|
| `operating_cash_flow` | `int` | Cash flow from operations |
| `investing_cash_flow` | `int` | Cash flow from investing |
| `financing_cash_flow` | `int` | Cash flow from financing |
| `fcf` | `int` | Free cash flow (operating CF + investing CF, auto-calculated) |

**Auto-calculated Ratios**

| Property | Type | Description |
|----------|------|-------------|
| `debt_ratio` | `float \| None` | Debt ratio (total liabilities / total equity) |
| `current_ratio` | `float \| None` | Current ratio (current assets / current liabilities) |
| `operating_margin` | `float \| None` | Operating margin (operating income / revenue) |
| `net_margin` | `float \| None` | Net margin (net income / revenue) |
| `roe` | `float \| None` | Return on equity (net income / total equity) |
| `roa` | `float \| None` | Return on assets (net income / total assets) |
| `revenue_growth` | `float \| None` | Revenue growth rate (vs. previous period) |
| `net_income_growth` | `float \| None` | Net income growth rate (vs. previous period) |

> Ratio properties return `None` when the denominator is zero or negative.

```python
data = financials_to_dict(parsed)  # Convert to dict for API responses
# → {"balance_sheet": {...}, "income_statement": {...}, "cash_flow": {...}, "ratios": {...}, "growth": {...}}
```

### Report Types

| Key | Description |
|-----|-------------|
| `"annual"` | Annual report |
| `"half"` | Semi-annual report |
| `"q1"` | Q1 report |
| `"q3"` | Q3 report |

### Consolidated vs Separate

The `consolidated` parameter of `get_financial_statements()`:

| Value | Description |
|-------|-------------|
| `True` (default) | Consolidated financial statements (includes subsidiaries) |
| `False` | Separate financial statements (parent entity only) |

Consolidated statements (`True`) are recommended for most analyses. Separate statements are used in special cases such as holding company analysis.

## Important Notes

### Financial Statement Parser Limitations

- The parser works by **matching Korean account names** from DART (e.g., "Revenue", "Total Assets" in Korean).
- It works correctly for most listed companies, but some companies using non-standard account names may have missing fields.
- Financial sector companies (banks, insurance, securities) have different financial statement structures, and the parser may not recognize some items.

### Async Only

This library is `async/await` only. To use it from synchronous code:

```python
import asyncio
result = asyncio.run(main())
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `DART_API_KEY` | DART OpenAPI authentication key ([Get one here](https://opendart.fss.or.kr/)) |

## Comparison with Alternatives

| Feature | dart-enhanced | opendartreader | dart-fss |
|---------|:---:|:---:|:---:|
| Async | O | X | X |
| pandas-free | O | X | X |
| Type hints | O | Partial | Partial |
| Financial parser | O | X | O |
| Auto ratios (ROE, etc.) | O | X | X |
| Lightweight | O | X | X |

## DART API Key

1. Go to [DART OpenAPI](https://opendart.fss.or.kr/)
2. Sign up and apply for an authentication key
3. Set the issued key as the `DART_API_KEY` environment variable or pass it to `DartClient(api_key="...")`

## Disclaimer

This library is a technical tool for querying the DART OpenAPI and does not provide investment advice or financial services. Users are responsible for complying with the [DART OpenAPI Terms of Use](https://opendart.fss.or.kr/) and applicable laws.

## License

MIT License. See [LICENSE](LICENSE).
