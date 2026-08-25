"""
Currency Converter tool for AI Tool-Calling Assistant.
Supports live exchange rate conversions using free public REST APIs with offline fallback rates.
"""

import requests
import json
from typing import Dict, Any, Optional

# Supported major currencies with symbols and full names
CURRENCY_METADATA: Dict[str, Dict[str, str]] = {
    "USD": {"symbol": "$", "name": "US Dollar", "flag": "🇺🇸"},
    "EUR": {"symbol": "€", "name": "Euro", "flag": "🇪🇺"},
    "GBP": {"symbol": "£", "name": "British Pound", "flag": "🇬🇧"},
    "JPY": {"symbol": "¥", "name": "Japanese Yen", "flag": "🇯🇵"},
    "INR": {"symbol": "₹", "name": "Indian Rupee", "flag": "🇮🇳"},
    "CAD": {"symbol": "CA$", "name": "Canadian Dollar", "flag": "🇨🇦"},
    "AUD": {"symbol": "AU$", "name": "Australian Dollar", "flag": "🇦🇺"},
    "CHF": {"symbol": "CHF", "name": "Swiss Franc", "flag": "🇨🇭"},
    "CNY": {"symbol": "CN¥", "name": "Chinese Yuan", "flag": "🇨🇳"},
    "SGD": {"symbol": "SG$", "name": "Singapore Dollar", "flag": "🇸🇬"},
    "NZD": {"symbol": "NZ$", "name": "New Zealand Dollar", "flag": "🇳🇿"},
    "AED": {"symbol": "AED", "name": "UAE Dirham", "flag": "🇦🇪"},
    "BRL": {"symbol": "R$", "name": "Brazilian Real", "flag": "🇧🇷"},
    "KRW": {"symbol": "₩", "name": "South Korean Won", "flag": "🇰🇷"},
    "MXN": {"symbol": "MX$", "name": "Mexican Peso", "flag": "🇲🇽"},
    "SEK": {"symbol": "kr", "name": "Swedish Krona", "flag": "🇸🇪"},
    "NOK": {"symbol": "kr", "name": "Norwegian Krone", "flag": "🇳🇴"},
    "TRY": {"symbol": "₺", "name": "Turkish Lira", "flag": "🇹🇷"},
    "ZAR": {"symbol": "R", "name": "South African Rand", "flag": "🇿🇦"},
    "HKD": {"symbol": "HK$", "name": "Hong Kong Dollar", "flag": "🇭🇰"},
}

# Reliable baseline exchange rates relative to 1 USD for offline resilience
FALLBACK_USD_RATES: Dict[str, float] = {
    "USD": 1.0,
    "EUR": 0.92,
    "GBP": 0.79,
    "JPY": 154.50,
    "INR": 86.80,
    "CAD": 1.38,
    "AUD": 1.53,
    "CHF": 0.89,
    "CNY": 7.24,
    "SGD": 1.34,
    "NZD": 1.68,
    "AED": 3.67,
    "BRL": 5.65,
    "KRW": 1380.0,
    "MXN": 19.80,
    "SEK": 10.60,
    "NOK": 10.90,
    "TRY": 34.20,
    "ZAR": 18.10,
    "HKD": 7.78,
}


def convert_currency(amount: float, from_currency: str, to_currency: str) -> str:
    """
    Converts a monetary amount between two currencies using real-time exchange rates.

    Supported currencies include: USD, EUR, GBP, JPY, INR, CAD, AUD, CHF, CNY, SGD, NZD, AED, BRL, KRW, MXN, etc.

    Args:
        amount: The numerical quantity of money to convert (e.g. 100.0).
        from_currency: The 3-letter currency code to convert from (e.g. "USD", "EUR", "INR").
        to_currency: The 3-letter currency code to convert to (e.g. "EUR", "GBP", "JPY").

    Returns:
        A structured string containing converted amount, exchange rate, and timestamp.
    """
    from_curr = from_currency.strip().upper()
    to_curr = to_currency.strip().upper()

    if amount < 0:
        return f"Currency Error: Amount cannot be negative ({amount})."

    if from_curr == to_curr:
        symbol = CURRENCY_METADATA.get(from_curr, {}).get("symbol", from_curr)
        return f"Converted: {amount:,.2f} {from_curr} = {amount:,.2f} {to_curr} (Rate: 1.0000)"

    # Attempt 1: Fetch live exchange rate from Frankfurter API
    try:
        url = f"https://api.frankfurter.app/latest?amount={amount}&from={from_curr}&to={to_curr}"
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            rates = data.get("rates", {})
            if to_curr in rates:
                converted_val = rates[to_curr]
                rate_per_unit = converted_val / amount if amount != 0 else 0
                inverse_rate = 1 / rate_per_unit if rate_per_unit != 0 else 0
                date = data.get("date", "latest")

                from_meta = CURRENCY_METADATA.get(from_curr, {"symbol": from_curr, "flag": ""})
                to_meta = CURRENCY_METADATA.get(to_curr, {"symbol": to_curr, "flag": ""})

                return (
                    f"💱 Currency Conversion ({date}):\n"
                    f"• {from_meta.get('flag', '')} {amount:,.2f} {from_curr} ({from_meta.get('symbol', '')}) = "
                    f"{to_meta.get('flag', '')} {converted_val:,.2f} {to_curr} ({to_meta.get('symbol', '')})\n"
                    f"• Exchange Rate: 1 {from_curr} = {rate_per_unit:,.4f} {to_curr}\n"
                    f"• Inverse Rate: 1 {to_curr} = {inverse_rate:,.4f} {from_curr}"
                )
    except Exception:
        pass

    # Attempt 2: Open ExchangeRate API fallback
    try:
        url = f"https://open.er-api.com/v6/latest/{from_curr}"
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            rates = data.get("rates", {})
            if to_curr in rates:
                rate_per_unit = float(rates[to_curr])
                converted_val = amount * rate_per_unit
                inverse_rate = 1 / rate_per_unit if rate_per_unit != 0 else 0

                from_meta = CURRENCY_METADATA.get(from_curr, {"symbol": from_curr, "flag": ""})
                to_meta = CURRENCY_METADATA.get(to_curr, {"symbol": to_curr, "flag": ""})

                return (
                    f"💱 Currency Conversion (Live Rate):\n"
                    f"• {from_meta.get('flag', '')} {amount:,.2f} {from_curr} = "
                    f"{to_meta.get('flag', '')} {converted_val:,.2f} {to_curr}\n"
                    f"• Exchange Rate: 1 {from_curr} = {rate_per_unit:,.4f} {to_curr}\n"
                    f"• Inverse Rate: 1 {to_curr} = {inverse_rate:,.4f} {from_curr}"
                )
    except Exception:
        pass

    # Attempt 3: Robust Offline Fallback using cached USD parity table
    if from_curr in FALLBACK_USD_RATES and to_curr in FALLBACK_USD_RATES:
        from_usd_rate = FALLBACK_USD_RATES[from_curr]
        to_usd_rate = FALLBACK_USD_RATES[to_curr]
        # Cross rate
        rate_per_unit = to_usd_rate / from_usd_rate
        converted_val = amount * rate_per_unit
        inverse_rate = 1 / rate_per_unit if rate_per_unit != 0 else 0

        from_meta = CURRENCY_METADATA.get(from_curr, {"symbol": from_curr, "flag": ""})
        to_meta = CURRENCY_METADATA.get(to_curr, {"symbol": to_curr, "flag": ""})

        return (
            f"💱 Currency Conversion (Offline Reference Rate):\n"
            f"• {from_meta.get('flag', '')} {amount:,.2f} {from_curr} = "
            f"{to_meta.get('flag', '')} {converted_val:,.2f} {to_curr}\n"
            f"• Estimated Rate: 1 {from_curr} ≈ {rate_per_unit:,.4f} {to_curr}\n"
            f"• Inverse Rate: 1 {to_curr} ≈ {inverse_rate:,.4f} {from_curr}"
        )

    return f"Currency Error: Unsupported currency conversion from '{from_currency}' to '{to_currency}'. Supported currencies: {', '.join(FALLBACK_USD_RATES.keys())}"
