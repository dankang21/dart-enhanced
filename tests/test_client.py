"""dart_enhanced.client 유닛 테스트 (네트워크 불필요)."""

import pytest
from dart_enhanced import DartClient, DartApiError
from dart_enhanced.client import _parse_amount, _classify_statement


class TestParseAmount:
    def test_normal(self):
        assert _parse_amount("1,234,567") == 1234567

    def test_negative(self):
        assert _parse_amount("-500,000") == -500000

    def test_none(self):
        assert _parse_amount(None) == 0

    def test_empty(self):
        assert _parse_amount("") == 0

    def test_spaces(self):
        assert _parse_amount(" 1 000 ") == 1000

    def test_invalid(self):
        assert _parse_amount("N/A") == 0


class TestClassifyStatement:
    def test_bs(self):
        assert _classify_statement("BS") == "BS"

    def test_cis(self):
        assert _classify_statement("CIS") == "IS"

    def test_cf(self):
        assert _classify_statement("CF") == "CF"

    def test_unknown(self):
        assert _classify_statement("XYZ") == "XYZ"


class TestDartClientInit:
    def test_no_api_key_raises(self):
        with pytest.raises(ValueError, match="DART API 키"):
            DartClient(api_key="")

    def test_with_api_key(self):
        client = DartClient(api_key="test-key-12345")
        assert client.api_key == "test-key-12345"


class TestDartApiError:
    def test_message(self):
        err = DartApiError("test error", "013")
        assert str(err) == "test error"
        assert err.status_code == "013"
