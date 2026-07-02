#!/usr/bin/env python3
"""Fetch BTC daily history with explicit provenance.

Primary: CoinMetrics community BTC CSV, because it includes early BTC history and
useful on-chain fields like MVRV.
Fallback: Coinbase Exchange daily candles, which are live but only start around
2015. Never synthetic. If both fail, fail loudly.
"""
from __future__ import annotations

import csv
import io
import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)
OUT_CSV = RAW_DIR / "btc_usd_daily.csv"
META_JSON = RAW_DIR / "btc_usd_daily.meta.json"

COINMETRICS_URL = "https://raw.githubusercontent.com/coinmetrics/data/master/csv/btc.csv"
PRODUCT = "BTC-USD"
GRANULARITY = 86400
COINBASE_START = datetime(2015, 1, 1, tzinfo=timezone.utc)
END = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
CHUNK_DAYS = 299


def request_text(url: str, timeout: int = 60) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "btc-log-regression-dashboard/0.2"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        if resp.status != 200:
            raise RuntimeError(f"HTTP {resp.status} for {url}")
        return resp.read().decode("utf-8")


def parse_float(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def as_float(value: object) -> float:
    if isinstance(value, (int, float, str)):
        return float(value)
    raise TypeError(f"Expected numeric value, got {type(value).__name__}")


def fetch_coinmetrics() -> tuple[list[dict[str, object]], dict[str, object]]:
    text = request_text(COINMETRICS_URL)
    rows: list[dict[str, object]] = []
    reader = csv.DictReader(io.StringIO(text))
    for row in reader:
        close = parse_float(row.get("PriceUSD")) or parse_float(row.get("ReferenceRateUSD"))
        if close is None or close <= 0:
            continue
        # CoinMetrics has early blockchain rows before meaningful USD pricing; keep priced rows only.
        rows.append(
            {
                "date": row["time"],
                "open": close,
                "high": close,
                "low": close,
                "close": close,
                "volume_btc": parse_float(row.get("volume_reported_spot_usd_1d")),
                "mvrv": parse_float(row.get("CapMVRVCur")),
                "realized_cap_usd": parse_float(row.get("CapRealUSD")),
                "market_cap_usd": parse_float(row.get("CapMrktCurUSD")),
                "source": "coinmetrics-community",
            }
        )
    rows.sort(key=lambda r: str(r["date"]))
    if len(rows) < 3000:
        raise RuntimeError(f"CoinMetrics returned too few priced BTC rows: {len(rows)}")
    meta = {
        "source": "CoinMetrics community BTC CSV",
        "source_url": COINMETRICS_URL,
        "provenance": "live-public-full-history",
        "rows": len(rows),
        "first_date": rows[0]["date"],
        "last_date": rows[-1]["date"],
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "fields": ["PriceUSD", "CapMVRVCur", "CapMrktCurUSD", "volume_reported_spot_usd_1d"],
        "limitation": "Daily CoinMetrics community data may lag current spot by a day; use Coinbase/Binance spot overlay later if needed.",
    }
    return rows, meta


def fetch_coinbase_chunk(start: datetime, end: datetime) -> list[list[float]]:
    params = urllib.parse.urlencode(
        {
            "start": start.isoformat().replace("+00:00", "Z"),
            "end": end.isoformat().replace("+00:00", "Z"),
            "granularity": GRANULARITY,
        }
    )
    url = f"https://api.exchange.coinbase.com/products/{PRODUCT}/candles?{params}"
    req = urllib.request.Request(url, headers={"User-Agent": "btc-log-regression-dashboard/0.2"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        if resp.status != 200:
            raise RuntimeError(f"Coinbase returned HTTP {resp.status}")
        return json.loads(resp.read().decode("utf-8"))


def fetch_coinbase_spot() -> tuple[dict[str, object], dict[str, object]]:
    url = f"https://api.exchange.coinbase.com/products/{PRODUCT}/ticker"
    req = urllib.request.Request(url, headers={"User-Agent": "btc-log-regression-dashboard/0.2"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        if resp.status != 200:
            raise RuntimeError(f"Coinbase ticker returned HTTP {resp.status}")
        payload = json.loads(resp.read().decode("utf-8"))
    price = parse_float(payload.get("price"))
    if price is None or price <= 0:
        raise RuntimeError("Coinbase ticker returned an invalid BTC price")
    time_text = str(payload["time"]).replace("Z", "+00:00")
    if "." in time_text:
        head, tail = time_text.split(".", 1)
        frac, tz = tail.split("+", 1) if "+" in tail else (tail, "00:00")
        time_text = f"{head}.{frac[:6]}+{tz}"
    ticker_time = datetime.fromisoformat(time_text)
    row = {
        "date": ticker_time.date().isoformat(),
        "open": price,
        "high": price,
        "low": price,
        "close": price,
        "volume_btc": parse_float(payload.get("volume")),
        "mvrv": None,
        "realized_cap_usd": None,
        "market_cap_usd": None,
        "source": "coinbase-spot-ticker",
    }
    meta = {
        "source": "Coinbase Exchange ticker endpoint",
        "product": PRODUCT,
        "provenance": "live-public-spot-price",
        "price": price,
        "time": payload["time"],
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "limitation": "Hourly dashboard refresh treats the current day's close as provisional spot until the daily candle finalizes.",
    }
    return row, meta


def overlay_spot(rows: list[dict[str, object]], spot: dict[str, object]) -> list[dict[str, object]]:
    merged = list(rows)
    spot_date = str(spot["date"])
    spot_close = as_float(spot["close"])
    for row in reversed(merged):
        if str(row["date"]) == spot_date:
            row["close"] = spot_close
            row["high"] = max(as_float(row["high"]), spot_close)
            row["low"] = min(as_float(row["low"]), spot_close)
            if row.get("open") is None:
                row["open"] = spot_close
            row["volume_btc"] = row.get("volume_btc") or spot.get("volume_btc")
            row["source"] = "coinbase-daily-plus-spot-ticker"
            return merged
    if not merged or spot_date > str(merged[-1]["date"]):
        merged.append(spot)
        return merged
    return merged


def overlay_live_spot(rows: list[dict[str, object]], meta: dict[str, object]) -> tuple[list[dict[str, object]], dict[str, object]]:
    spot_row, spot_meta = fetch_coinbase_spot()
    merged = overlay_spot(rows, spot_row)
    enriched_meta = {
        **meta,
        "rows": len(merged),
        "last_date": merged[-1]["date"],
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "current_spot_source": spot_meta,
        "limitation": f"{meta.get('limitation', '')} Current-day BTC close is refreshed hourly from Coinbase spot and remains provisional until the daily candle finalizes.".strip(),
    }
    return merged, enriched_meta


def fetch_coinbase() -> tuple[list[dict[str, object]], dict[str, object]]:
    rows_by_date: dict[str, dict[str, object]] = {}
    current = COINBASE_START
    request_count = 0
    while current < END:
        chunk_end = min(current + timedelta(days=CHUNK_DAYS), END)
        candles = fetch_coinbase_chunk(current, chunk_end)
        request_count += 1
        for candle in candles:
            ts, low, high, open_, close, volume = candle
            dt = datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat()
            rows_by_date[dt] = {
                "date": dt,
                "open": float(open_),
                "high": float(high),
                "low": float(low),
                "close": float(close),
                "volume_btc": float(volume),
                "mvrv": None,
                "realized_cap_usd": None,
                "market_cap_usd": None,
                "source": "coinbase-exchange",
            }
        current = chunk_end + timedelta(days=1)
        time.sleep(0.15)
    rows = [rows_by_date[k] for k in sorted(rows_by_date)]
    if len(rows) < 1000:
        raise RuntimeError(f"Coinbase returned too few candles: {len(rows)}")
    meta = {
        "source": "Coinbase Exchange candles endpoint",
        "product": PRODUCT,
        "granularity_seconds": GRANULARITY,
        "provenance": "live-public-partial-history",
        "rows": len(rows),
        "first_date": rows[0]["date"],
        "last_date": rows[-1]["date"],
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "request_count": request_count,
        "limitation": "Coinbase spot history starts around 2015; use CoinMetrics/backfill for the final long-term model.",
    }
    return rows, meta


def write_rows(rows: list[dict[str, object]], meta: dict[str, object]) -> None:
    fields = ["date", "open", "high", "low", "close", "volume_btc", "mvrv", "realized_cap_usd", "market_cap_usd", "source"]
    with OUT_CSV.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    META_JSON.write_text(json.dumps(meta, indent=2))


def main() -> int:
    errors: list[str] = []
    try:
        cm_rows, cm_meta = fetch_coinmetrics()
        try:
            cb_rows, cb_meta = fetch_coinbase()
            cm_last = str(cm_rows[-1]["date"])
            merged = list(cm_rows)
            merged.extend(row for row in cb_rows if str(row["date"]) > cm_last)
            merged.sort(key=lambda r: str(r["date"]))
            meta = {
                **cm_meta,
                "source": "CoinMetrics community BTC CSV + Coinbase Exchange recent candles + Coinbase spot ticker",
                "provenance": "live-public-full-history-with-recent-coinbase-overlay-and-spot",
                "rows": len(merged),
                "first_date": merged[0]["date"],
                "last_date": merged[-1]["date"],
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "primary_source": cm_meta,
                "recent_overlay_source": cb_meta,
                "limitation": "Recent Coinbase overlay has no MVRV/on-chain fields; on-chain values are shown as latest available, not faked.",
            }
            merged, meta = overlay_live_spot(merged, meta)
            write_rows(merged, meta)
            print(json.dumps({"selected_feed": "coinmetrics+coinbase+spot", **meta}, indent=2))
            return 0
        except Exception as exc:  # noqa: BLE001
            errors.append(f"coinbase recent overlay/spot: {exc}")
            cm_rows, cm_meta = overlay_live_spot(cm_rows, cm_meta)
            write_rows(cm_rows, cm_meta)
            print(json.dumps({"selected_feed": "coinmetrics+spot", "overlay_warning": errors[-1], **cm_meta}, indent=2))
            return 0
    except Exception as exc:  # noqa: BLE001
        errors.append(f"coinmetrics: {exc}")

    try:
        rows, meta = fetch_coinbase()
        rows, meta = overlay_live_spot(rows, meta)
        write_rows(rows, meta)
        print(json.dumps({"selected_feed": "coinbase+spot", **meta}, indent=2))
        return 0
    except Exception as exc:  # noqa: BLE001
        errors.append(f"coinbase/spot: {exc}")

    raise RuntimeError("All real BTC history feeds failed: " + " | ".join(errors))


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
