#!/usr/bin/env python3
"""Build the BTC macro-cycle sequence described in the linked video.

Live/no-key inputs:
- Copper and gold futures, plus WTI crude: Yahoo Finance chart endpoint
- BTC implied volatility (DVOL): Deribit public API
- BTC 90-day realized volatility: local BTC daily history

ISM Manufacturing PMI is an explicit manual snapshot because the official ISM feed
is not available here as a stable no-key machine-readable endpoint. The dashboard
labels that limitation rather than pretending the number is live.
"""
from __future__ import annotations

import csv
import json
import math
import statistics
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_PATH = ROOT / "public" / "data" / "macro-cycle.json"
MANUAL_PATH = ROOT / "data" / "manual" / "macro-cycle.json"
BTC_PATH = ROOT / "data" / "raw" / "btc.csv"


def request_json(url: str, timeout: int = 45) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 multi-asset-cycle-dashboard/0.2"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        if response.status != 200:
            raise RuntimeError(f"HTTP {response.status}: {url}")
        return json.loads(response.read().decode("utf-8"))


def yahoo_series(symbol: str) -> tuple[list[dict[str, float | str]], dict[str, object]]:
    period2 = int(time.time()) + 86400
    encoded = urllib.parse.quote(symbol, safe="")
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded}"
        f"?period1=0&period2={period2}&interval=1d&events=history&includeAdjustedClose=true"
    )
    result = request_json(url)["chart"]["result"][0]
    timestamps = result.get("timestamp") or []
    closes = result.get("indicators", {}).get("quote", [{}])[0].get("close") or []
    rows = []
    for timestamp, close in zip(timestamps, closes):
        if close is None or float(close) <= 0:
            continue
        rows.append({"date": datetime.fromtimestamp(timestamp, timezone.utc).date().isoformat(), "value": float(close)})
    meta = result.get("meta", {})
    spot = meta.get("regularMarketPrice")
    spot_time = meta.get("regularMarketTime")
    if spot and rows:
        spot_date = datetime.fromtimestamp(spot_time, timezone.utc).date().isoformat() if spot_time else datetime.now(timezone.utc).date().isoformat()
        if spot_date == rows[-1]["date"]:
            rows[-1]["value"] = float(spot)
        elif spot_date > rows[-1]["date"]:
            rows.append({"date": spot_date, "value": float(spot)})
    return rows, {"source": "Yahoo Finance chart endpoint", "source_url": url, "symbol": symbol, "fetched_at": datetime.now(timezone.utc).isoformat()}


def btc_closes() -> list[dict[str, float | str]]:
    rows = []
    with BTC_PATH.open() as handle:
        for row in csv.DictReader(handle):
            try:
                close = float(row["close"])
            except (TypeError, ValueError):
                continue
            if close > 0:
                rows.append({"date": row["date"], "value": close})
    return rows


def realized_volatility(rows: list[dict[str, float | str]], window: int = 90) -> list[dict[str, float | str]]:
    returns = [math.log(float(rows[i]["value"]) / float(rows[i - 1]["value"])) for i in range(1, len(rows))]
    output = []
    for i in range(window, len(returns) + 1):
        annualized = statistics.pstdev(returns[i - window:i]) * math.sqrt(365) * 100
        output.append({"date": rows[i]["date"], "value": round(annualized, 2)})
    return output


def dvol_latest() -> tuple[float, str, dict[str, object]]:
    end = int(time.time() * 1000)
    start = end - (14 * 86400 * 1000)
    url = (
        "https://www.deribit.com/api/v2/public/get_volatility_index_data"
        f"?currency=BTC&start_timestamp={start}&end_timestamp={end}&resolution=3600"
    )
    data = request_json(url)["result"]["data"]
    if not data:
        raise RuntimeError("Deribit returned no DVOL observations")
    latest = data[-1]
    date = datetime.fromtimestamp(latest[0] / 1000, timezone.utc).isoformat()
    return round(float(latest[4]), 2), date, {"source": "Deribit DVOL public API", "source_url": url, "fetched_at": datetime.now(timezone.utc).isoformat()}


def align_ratio(numerator: list[dict[str, float | str]], denominator: list[dict[str, float | str]]) -> list[dict[str, float | str]]:
    den = {str(row["date"]): float(row["value"]) for row in denominator}
    return [
        {"date": str(row["date"]), "value": round(float(row["value"]) / den[str(row["date"])], 8)}
        for row in numerator if str(row["date"]) in den and den[str(row["date"])] > 0
    ]


def linreg(values: list[float]) -> tuple[float, float]:
    xs = list(range(len(values)))
    xbar = statistics.mean(xs)
    ybar = statistics.mean(values)
    denominator = sum((x - xbar) ** 2 for x in xs)
    slope = sum((x - xbar) * (y - ybar) for x, y in zip(xs, values)) / denominator
    return ybar - slope * xbar, slope


def copper_breakout(ratio: list[dict[str, float | str]]) -> dict[str, object]:
    lookback = ratio[-756:] if len(ratio) >= 756 else ratio
    training = lookback[:-20] if len(lookback) > 80 else lookback[:-1]
    values = [float(row["value"]) for row in training]
    intercept, slope = linreg(values)
    predicted = intercept + slope * (len(lookback) - 1)
    latest = float(lookback[-1]["value"])
    ma200_values = [float(row["value"]) for row in ratio[-200:]]
    ma200 = statistics.mean(ma200_values)
    distance = (latest / predicted - 1) * 100
    fired = latest > predicted * 1.02 and latest > ma200
    return {
        "value": round(latest, 6),
        "date": lookback[-1]["date"],
        "trendline": round(predicted, 6),
        "ma_200d": round(ma200, 6),
        "distance_above_3y_trend_pct": round(distance, 2),
        "status": "fired" if fired else "watching",
        "detail": "Above the three-year regression trendline and 200D average." if fired else "Not yet above both the three-year regression trendline and 200D average.",
        "method": "Breakout = ratio > 2% above a three-year linear trendline and above its 200D moving average.",
    }


def percentile_rank(values: list[float], latest: float) -> float:
    return 100 * sum(value <= latest for value in values) / len(values)


def load_previous() -> dict[str, Any]:
    try:
        return json.loads(PUBLIC_PATH.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def main() -> int:
    manual = json.loads(MANUAL_PATH.read_text())
    previous = load_previous()
    errors: list[str] = []

    try:
        copper, copper_meta = yahoo_series("HG=F")
        gold, gold_meta = yahoo_series("GC=F")
        oil, oil_meta = yahoo_series("CL=F")
        ratio = align_ratio(copper, gold)
        copper_signal = copper_breakout(ratio)
    except Exception as exc:  # keep scheduled refresh resilient
        errors.append(f"market proxies: {exc}")
        prior = previous.get("indicators", {}) if isinstance(previous, dict) else {}
        copper_signal = dict(prior.get("copper_gold", {}))
        ratio = list(copper_signal.get("series", []))
        oil = list(prior.get("oil", {}).get("series", []))
        copper_meta = gold_meta = oil_meta = {"source": "retained prior successful snapshot"}

    btc = btc_closes()
    rv = realized_volatility(btc)
    rv_latest = float(rv[-1]["value"])
    rv_percentile = percentile_rank([float(row["value"]) for row in rv], rv_latest)
    rv_status = "coiled" if rv_percentile <= 10 else "expanding" if len(rv) > 10 and rv_latest > float(rv[-10]["value"]) * 1.1 else "normal"

    try:
        dvol, dvol_date, dvol_meta = dvol_latest()
    except Exception as exc:
        errors.append(f"DVOL: {exc}")
        prior_dvol = previous.get("indicators", {}).get("btc_implied_volatility", {}) if isinstance(previous, dict) else {}
        dvol = float(prior_dvol.get("value", 0))
        dvol_date = str(prior_dvol.get("date", "unavailable"))
        dvol_meta = {"source": "retained prior successful snapshot"}

    oil_latest = float(oil[-1]["value"]) if oil else 0
    oil_20d = float(oil[-21]["value"]) if len(oil) > 21 else oil_latest
    oil_change = (oil_latest / oil_20d - 1) * 100 if oil_20d else 0
    oil_status = "high risk" if oil_latest >= 100 else "elevated watch" if oil_latest >= 80 and oil_change > 5 else "contained"

    pmi = manual["ism_manufacturing_pmi"]
    pmi_fired = float(pmi["value"]) > 50
    btc_dashboard = json.loads((ROOT / "public" / "data" / "btc.json").read_text())
    btc_latest = btc_dashboard["latest"]
    top_fired = float(btc_latest["z_score"]) >= 1.5 and float(btc_latest.get("rsi_14d") or 0) >= 70
    top_status = "fired" if top_fired else "watching" if float(btc_latest["z_score"]) >= 0.5 else "not fired"

    sequence = [
        {"number": 1, "name": "US business cycle", "status": "fired" if pmi_fired else "watching", "detail": f"ISM Manufacturing PMI {pmi['value']} — {'expansion' if pmi_fired else 'contraction'} threshold is 50."},
        {"number": 2, "name": "Copper / gold breakout", "status": copper_signal.get("status", "unavailable"), "detail": copper_signal.get("detail", "Live proxy unavailable.")},
        {"number": 3, "name": "BTC volatility expansion", "status": "fired" if rv_status == "expanding" else rv_status if rv_status == "coiled" else "watching", "detail": f"90D realized volatility {rv_latest:.1f}%; historical percentile {rv_percentile:.1f}; DVOL {dvol:.1f}%."},
        {"number": 4, "name": "BTC cycle top", "status": top_status, "detail": f"Objective proxy: log z-score {btc_latest['z_score']} and RSI {btc_latest.get('rsi_14d')}; fires when z ≥ 1.5 and RSI ≥ 70."},
    ]
    fired_count = sum(item["status"] == "fired" for item in sequence)

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "framework": {
            "name": "BTC Macro Domino Sequence",
            "source_video": "https://youtu.be/rzZ1AmdWhaY",
            "summary": "Business cycle turns higher → copper outperforms gold → BTC volatility expands → BTC reaches a cycle top.",
            "fired_count": fired_count,
            "sequence": sequence,
            "warning": "Research framework and decision support only. Thresholds are transparent dashboard rules, not investment advice.",
        },
        "indicators": {
            "ism_pmi": {**pmi, "threshold": 50, "status": "expansion" if pmi_fired else "contraction"},
            "copper_gold": {**copper_signal, "series": ratio[-520:]},
            "btc_realized_volatility": {"value": round(rv_latest, 2), "date": rv[-1]["date"], "historical_percentile": round(rv_percentile, 2), "status": rv_status, "series": rv[-520:], "method": "90-day standard deviation of daily log returns, annualized with √365."},
            "btc_implied_volatility": {"value": dvol, "date": dvol_date, "status": "low / coiled" if dvol < 40 else "normal" if dvol < 65 else "elevated", "source": dvol_meta},
            "oil": {"value": round(oil_latest, 2), "date": oil[-1]["date"] if oil else "unavailable", "change_20d_pct": round(oil_change, 2), "status": oil_status, "series": oil[-520:], "rule": "Elevated watch above $80 with >5% 20-session rise; high risk at/above $100."},
        },
        "sources": {"copper": copper_meta, "gold": gold_meta, "oil": oil_meta, "implied_volatility": dvol_meta, "pmi": pmi.get("source")},
        "refresh_errors": errors,
    }
    PUBLIC_PATH.parent.mkdir(parents=True, exist_ok=True)
    PUBLIC_PATH.write_text(json.dumps(payload, indent=2))
    print(json.dumps({"output": str(PUBLIC_PATH), "fired_count": fired_count, "oil_status": oil_status, "realized_vol_percentile": round(rv_percentile, 2), "errors": errors}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
