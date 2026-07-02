#!/usr/bin/env python3
"""Fetch daily market data for the multi-asset cycle dashboard.

BTC uses the local CoinMetrics + Coinbase fetcher copied from the Bitcoin dashboard.
Traditional assets use Yahoo Finance's no-key chart endpoint with explicit provenance.
"""
from __future__ import annotations

import csv
import importlib.util
import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

ASSETS: list[dict[str, str]] = [
    {"id": "btc", "name": "Bitcoin", "symbol": "BTC-USD", "type": "crypto"},
    {"id": "gold", "name": "Gold", "symbol": "GLD", "type": "etf", "proxy_note": "ETF proxy for gold spot"},
    {"id": "silver", "name": "Silver", "symbol": "SLV", "type": "etf", "proxy_note": "ETF proxy for silver spot"},
    {"id": "mags", "name": "Roundhill Magnificent Seven ETF", "symbol": "MAGS", "type": "etf"},
    {"id": "sp500", "name": "S&P 500 Index", "symbol": "^GSPC", "type": "index"},
    {"id": "nasdaq", "name": "NASDAQ Composite", "symbol": "^IXIC", "type": "index"},
]


def request_json(url: str, timeout: int = 90) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 multi-asset-cycle-dashboard/0.1"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"HTTP {resp.status} for {url}")
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            time.sleep(1 + attempt)
    raise RuntimeError(f"request failed after retries for {url}: {last_error}")


def fetch_yahoo_daily(asset: dict[str, str]) -> tuple[list[dict[str, object]], dict[str, object]]:
    symbol = asset["symbol"]
    period2 = int(time.time()) + 86400
    encoded = urllib.parse.quote(symbol, safe="")
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded}"
        f"?period1=0&period2={period2}&interval=1d&events=history&includeAdjustedClose=true"
    )
    payload = request_json(url)
    chart = payload.get("chart", {})
    if chart.get("error"):
        raise RuntimeError(f"Yahoo chart error for {symbol}: {chart['error']}")
    result = (chart.get("result") or [None])[0]
    if not result:
        raise RuntimeError(f"Yahoo returned no chart result for {symbol}")
    timestamps = result.get("timestamp") or []
    quote = result.get("indicators", {}).get("quote", [{}])[0]
    adjclose = result.get("indicators", {}).get("adjclose", [{}])[0].get("adjclose") or []
    meta = result.get("meta", {})
    rows: list[dict[str, object]] = []
    for i, ts in enumerate(timestamps):
        close = _at(quote.get("close"), i)
        if close is None or close <= 0:
            continue
        dt = datetime.fromtimestamp(int(ts), tz=timezone.utc).date().isoformat()
        rows.append(
            {
                "date": dt,
                "open": _at(quote.get("open"), i) or close,
                "high": _at(quote.get("high"), i) or close,
                "low": _at(quote.get("low"), i) or close,
                "close": close,
                "adj_close": _at(adjclose, i) or close,
                "volume": _at(quote.get("volume"), i),
                "source": "yahoo-chart-no-key",
            }
        )
    rows.sort(key=lambda row: str(row["date"]))
    if len(rows) < 120:
        raise RuntimeError(f"Yahoo returned too few daily rows for {symbol}: {len(rows)}")
    spot_price = _at([meta.get("regularMarketPrice")], 0)
    spot_time = meta.get("regularMarketTime")
    if spot_price is not None and spot_price > 0:
        spot_date = datetime.fromtimestamp(int(spot_time), tz=timezone.utc).date().isoformat() if spot_time else datetime.now(timezone.utc).date().isoformat()
        if spot_date >= str(rows[-1]["date"]):
            if spot_date == str(rows[-1]["date"]):
                rows[-1]["close"] = spot_price
                rows[-1]["adj_close"] = spot_price
                rows[-1]["high"] = max(float(str(rows[-1]["high"])), spot_price)
                rows[-1]["low"] = min(float(str(rows[-1]["low"])), spot_price)
                rows[-1]["source"] = "yahoo-chart-plus-regular-market-price"
            else:
                rows.append(
                    {
                        "date": spot_date,
                        "open": spot_price,
                        "high": spot_price,
                        "low": spot_price,
                        "close": spot_price,
                        "adj_close": spot_price,
                        "volume": None,
                        "source": "yahoo-regular-market-price",
                    }
                )
    provenance = {
        "source": "Yahoo Finance chart endpoint",
        "source_url": url,
        "provenance": "live-public-no-key-daily-history",
        "asset_id": asset["id"],
        "name": asset["name"],
        "symbol": symbol,
        "type": asset["type"],
        "currency": meta.get("currency", "USD"),
        "exchange": meta.get("exchangeName"),
        "instrument_type": meta.get("instrumentType"),
        "regular_market_price": meta.get("regularMarketPrice"),
        "regular_market_time": meta.get("regularMarketTime"),
        "rows": len(rows),
        "first_date": rows[0]["date"],
        "last_date": rows[-1]["date"],
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "limitation": "No-key Yahoo chart endpoint; current-day close may be a provisional regular-market price until the daily bar finalizes. Expect occasional availability/rate-limit issues.",
    }
    if asset.get("proxy_note"):
        provenance["proxy_note"] = asset["proxy_note"]
    return rows, provenance


def _at(values: Any, i: int) -> float | None:
    if not isinstance(values, list) or i >= len(values):
        return None
    value = values[i]
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def write_asset_csv(asset_id: str, rows: list[dict[str, object]], meta: dict[str, object]) -> None:
    fields = ["date", "open", "high", "low", "close", "adj_close", "volume", "source"]
    with (RAW_DIR / f"{asset_id}.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    (RAW_DIR / f"{asset_id}.meta.json").write_text(json.dumps(meta, indent=2))


def run_btc_fetch() -> dict[str, object]:
    module_path = ROOT / "scripts" / "fetch_btc_history.py"
    spec = importlib.util.spec_from_file_location("fetch_btc_history", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    code = module.main()
    if code != 0:
        raise RuntimeError(f"BTC fetch returned {code}")
    src_csv = RAW_DIR / "btc_usd_daily.csv"
    dst_csv = RAW_DIR / "btc.csv"
    rows: list[dict[str, object]] = []
    with src_csv.open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(
                {
                    "date": row["date"],
                    "open": row["open"],
                    "high": row["high"],
                    "low": row["low"],
                    "close": row["close"],
                    "adj_close": row["close"],
                    "volume": row.get("volume_btc") or "",
                    "source": row.get("source") or "btc-feed",
                    "mvrv": row.get("mvrv") or "",
                    "market_cap_usd": row.get("market_cap_usd") or "",
                    "realized_cap_usd": row.get("realized_cap_usd") or "",
                }
            )
    fields = ["date", "open", "high", "low", "close", "adj_close", "volume", "source", "mvrv", "market_cap_usd", "realized_cap_usd"]
    with dst_csv.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    meta = json.loads((RAW_DIR / "btc_usd_daily.meta.json").read_text())
    meta = {
        **meta,
        "asset_id": "btc",
        "name": "Bitcoin",
        "symbol": "BTC-USD",
        "type": "crypto",
        "currency": "USD",
    }
    (RAW_DIR / "btc.meta.json").write_text(json.dumps(meta, indent=2))
    return meta


def main() -> int:
    results: list[dict[str, object]] = []
    errors: list[str] = []
    for asset in ASSETS:
        try:
            if asset["id"] == "btc":
                meta = run_btc_fetch()
            else:
                rows, meta = fetch_yahoo_daily(asset)
                write_asset_csv(asset["id"], rows, meta)
            results.append({"asset_id": asset["id"], "symbol": asset["symbol"], "rows": meta.get("rows"), "last_date": meta.get("last_date"), "source": meta.get("source")})
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{asset['id']}: {exc}")
    out = {"fetched_at": datetime.now(timezone.utc).isoformat(), "assets": results, "errors": errors}
    print(json.dumps(out, indent=2))
    if errors:
        raise RuntimeError("Some asset fetches failed: " + " | ".join(errors))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
