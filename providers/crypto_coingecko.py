from __future__ import annotations

import re
from datetime import datetime

import requests


class CryptoCoingeckoProvider:
    name = "coingecko"

    def get_historical_btc_price(self, prompt: str) -> dict | None:
        date = _extract_date(prompt)
        if not date:
            return None

        url = "https://api.coingecko.com/api/v3/coins/bitcoin/history"
        # Coingecko expects DD-MM-YYYY format.
        params = {"date": date.strftime("%d-%m-%Y"), "localization": "false"}
        resp = requests.get(url, params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        usd = data.get("market_data", {}).get("current_price", {}).get("usd")
        if usd is None:
            return None
        return {
            "provider": self.name,
            "date": date.strftime("%Y-%m-%d"),
            "currency": "USD",
            "price": usd,
        }


def _extract_date(prompt: str) -> datetime | None:
    m = re.search(r"(\d{1,2})(?:st|nd|rd|th)?\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+(\d{4})", prompt.lower())
    if not m:
        return None
    day = int(m.group(1))
    mon_str = m.group(2)
    year = int(m.group(3))
    mon_map = {
        "jan": 1,
        "feb": 2,
        "mar": 3,
        "apr": 4,
        "may": 5,
        "jun": 6,
        "jul": 7,
        "aug": 8,
        "sep": 9,
        "oct": 10,
        "nov": 11,
        "dec": 12,
    }
    return datetime(year, mon_map[mon_str], day)
