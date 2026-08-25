"""
Unit tests for the currency converter tool.
"""

import pytest
from app.tools.currency import convert_currency


def test_same_currency_conversion():
    res = convert_currency(100.0, "USD", "USD")
    assert "100.00 USD = 100.00 USD" in res


def test_standard_conversion_usd_to_eur():
    res = convert_currency(100.0, "USD", "EUR")
    assert "Currency Conversion" in res
    assert "EUR" in res
    assert "Exchange Rate" in res


def test_standard_conversion_usd_to_inr():
    res = convert_currency(50.0, "USD", "INR")
    assert "Currency Conversion" in res
    assert "INR" in res


def test_negative_amount_rejection():
    res = convert_currency(-50.0, "USD", "EUR")
    assert "Currency Error: Amount cannot be negative" in res


def test_unsupported_currency():
    res = convert_currency(100.0, "XYZ", "ABC")
    assert "Currency Error: Unsupported currency" in res
