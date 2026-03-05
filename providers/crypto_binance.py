from __future__ import annotations

import re
from datetime import datetime, timezone

import requests


class CryptoBinanceProvider:
    name = "binance"

    def get_historical_btc_price(self, prompt: str) -> dict | None:
        date = _extract_date(prompt)
        if not date:
            return None

        start_ms = int(datetime(date.year, date.month, date.day, tzinfo=timezone.utc).timestamp() * 1000)
        # 1d kline; we use close price from the day candle.
        url = "https://api.binance.com/api/v3/klines"
        params = {
            "symbol": "BTCUSDT",
            "interval": "1d",
            "startTime": start_ms,
            "limit": 1,
        }
        resp = requests.get(url, params=params, timeout=20)
        resp.raise_for_status()
        rows = resp.json()
        if not rows:
            return None
        close_price = float(rows[0][4])
        return {
            "provider": self.name,
            "date": date.strftime("%Y-%m-%d"),
            "currency": "USD",
            "price": close_price,
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
