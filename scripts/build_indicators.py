#!/usr/bin/env python3
"""Build multi-asset log-channel/rainbow/Elliott dashboard JSON."""
from __future__ import annotations

import csv
import json
import math
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
PUBLIC_DIR = ROOT / "public" / "data"
PUBLIC_DIR.mkdir(parents=True, exist_ok=True)

ASSETS = [
    {"id": "btc", "name": "Bitcoin", "symbol": "BTC-USD", "price_label": "BTC Price", "fit_start": "2015-01-01"},
    {"id": "gold", "name": "Gold", "symbol": "GLD", "price_label": "GLD Price", "fit_start": "2005-01-01"},
    {"id": "silver", "name": "Silver", "symbol": "SLV", "price_label": "SLV Price", "fit_start": "2007-01-01"},
    {"id": "mags", "name": "Roundhill Magnificent Seven ETF", "symbol": "MAGS", "price_label": "MAGS Price", "fit_start": "2023-04-11"},
    {"id": "mstr", "name": "Strategy (MicroStrategy)", "symbol": "MSTR", "price_label": "MSTR Price", "fit_start": "1998-06-11", "category": "Bitcoin Treasury Company"},
    {"id": "sp500", "name": "S&P 500 Index", "symbol": "^GSPC", "price_label": "S&P 500", "fit_start": "1990-01-01"},
    {"id": "nasdaq", "name": "NASDAQ Composite", "symbol": "^IXIC", "price_label": "NASDAQ", "fit_start": "1990-01-01"},
]

RAINBOW_BANDS = [
    ("Basically a Fire Sale", "#3b82f6"),
    ("BUY!", "#06b6d4"),
    ("Accumulate", "#22c55e"),
    ("Still Cheap", "#84cc16"),
    ("HODL!", "#facc15"),
    ("Is This a Bubble?", "#fb923c"),
    ("FOMO Intensifies", "#f97316"),
    ("Sell. Seriously, SELL!", "#ef4444"),
    ("Maximum Bubble Territory", "#991b1b"),
]


def parse_optional_float(value: str | None) -> float | None:
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


def read_rows(asset_id: str) -> list[dict[str, object]]:
    path = RAW_DIR / f"{asset_id}.csv"
    with path.open() as f:
        rows = []
        for row in csv.DictReader(f):
            close = parse_optional_float(row.get("close"))
            if close is None or close <= 0:
                continue
            rows.append(
                {
                    "date": row["date"],
                    "open": parse_optional_float(row.get("open")) or close,
                    "high": parse_optional_float(row.get("high")) or close,
                    "low": parse_optional_float(row.get("low")) or close,
                    "close": close,
                    "adj_close": parse_optional_float(row.get("adj_close")) or close,
                    "volume": parse_optional_float(row.get("volume")),
                    "source": row.get("source") or "market-feed",
                    "mvrv": parse_optional_float(row.get("mvrv")),
                    "market_cap_usd": parse_optional_float(row.get("market_cap_usd")),
                    "realized_cap_usd": parse_optional_float(row.get("realized_cap_usd")),
                }
            )
    rows.sort(key=lambda r: str(r["date"]))
    return rows


def linreg(xs: list[float], ys: list[float]) -> tuple[float, float]:
    xbar = statistics.mean(xs)
    ybar = statistics.mean(ys)
    denom = sum((x - xbar) ** 2 for x in xs)
    if denom == 0:
        raise ValueError("Cannot fit regression with zero x variance")
    slope = sum((x - xbar) * (y - ybar) for x, y in zip(xs, ys)) / denom
    intercept = ybar - slope * xbar
    return intercept, slope


def date_mask(rows: list[dict[str, object]], start: str) -> list[bool]:
    start_date = datetime.fromisoformat(start).date()
    return [datetime.fromisoformat(str(row["date"])).date() >= start_date for row in rows]


def percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    pos = (len(ordered) - 1) * q
    lower = math.floor(pos)
    upper = math.ceil(pos)
    if lower == upper:
        return ordered[int(pos)]
    weight = pos - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def moving_average(values: list[float], window: int) -> list[float | None]:
    out: list[float | None] = []
    total = 0.0
    for i, value in enumerate(values):
        total += value
        if i >= window:
            total -= values[i - window]
        out.append(total / window if i >= window - 1 else None)
    return out


def weekly_moving_average(rows: list[dict[str, object]], values: list[float], window_weeks: int) -> list[float | None]:
    out: list[float | None] = []
    weekly_closes: list[float] = []
    current_week: tuple[int, int] | None = None
    for row, value in zip(rows, values):
        dt = datetime.fromisoformat(str(row["date"])).date()
        week = dt.isocalendar()[:2]
        if week != current_week:
            weekly_closes.append(value)
            current_week = week
        else:
            weekly_closes[-1] = value
        out.append(sum(weekly_closes[-window_weeks:]) / window_weeks if len(weekly_closes) >= window_weeks else None)
    return out


def rounded_optional(value: float | None, digits: int = 2) -> float | None:
    return None if value is None else round(value, digits)


def rounded_object(value: object, digits: int = 2) -> float | None:
    if value is None:
        return None
    return round(as_float(value), digits)


def rsi(values: list[float], period: int = 14) -> list[float | None]:
    out: list[float | None] = [None] * len(values)
    if len(values) <= period:
        return out
    gains: list[float] = []
    losses: list[float] = []
    for i in range(1, period + 1):
        change = values[i] - values[i - 1]
        gains.append(max(change, 0.0))
        losses.append(abs(min(change, 0.0)))
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    out[period] = 100.0 if avg_loss == 0 else 100 - (100 / (1 + avg_gain / avg_loss))
    for i in range(period + 1, len(values)):
        change = values[i] - values[i - 1]
        gain = max(change, 0.0)
        loss = abs(min(change, 0.0))
        avg_gain = ((avg_gain * (period - 1)) + gain) / period
        avg_loss = ((avg_loss * (period - 1)) + loss) / period
        out[i] = 100.0 if avg_loss == 0 else 100 - (100 / (1 + avg_gain / avg_loss))
    return out


def zone_from_z(z: float) -> str:
    if z <= -2.0:
        return "Deep Value"
    if z <= -1.5:
        return "Accumulation"
    if z <= -0.5:
        return "Cheap"
    if z < 0.5:
        return "Fair"
    if z < 1.5:
        return "Warm"
    if z < 2.0:
        return "Expensive"
    return "Take Chips"


def zone_note(zone: str, asset_name: str) -> str:
    return {
        "Deep Value": f"{asset_name} is deeply below its log trend. Historically rare value territory for this model.",
        "Accumulation": f"{asset_name} is near the -1.5σ accumulation band.",
        "Cheap": f"{asset_name} is below trend but not at the deepest accumulation band.",
        "Fair": f"{asset_name} is near long-term trend fair value.",
        "Warm": f"{asset_name} is above trend. Upside can continue, but risk is rising.",
        "Expensive": f"{asset_name} is stretched above trend. Consider risk controls.",
        "Take Chips": f"{asset_name} is at/above the +2σ band. Historically hot territory.",
    }[zone]


def latest_non_null(series: Iterable[float | None]) -> float | None:
    for value in reversed(list(series)):
        if value is not None:
            return value
    return None


def rainbow_zone(residual: float, offsets: list[float]) -> str:
    if residual < offsets[0]:
        return "Below Fire Sale"
    for i, (label, _) in enumerate(RAINBOW_BANDS):
        if residual <= offsets[i + 1]:
            return label
    return "Above Maximum Bubble"


def build_rainbow(rows: list[dict[str, object]], xs: list[float], ys: list[float], fit_start: str) -> dict[str, object]:
    fit_mask = date_mask(rows, fit_start)
    fit_xs = [x for x, include in zip(xs, fit_mask) if include]
    fit_ys = [y for y, include in zip(ys, fit_mask) if include]
    if len(fit_xs) < 180:
        fit_xs = xs
        fit_ys = ys
        fit_start = str(rows[0]["date"])
    intercept, slope = linreg(fit_xs, fit_ys)
    log_trends = [intercept + slope * x for x in xs]
    residuals = [y - t for y, t in zip(ys, log_trends)]
    fit_residuals = [r for r, row in zip(residuals, rows) if str(row["date"]) >= fit_start]
    if len(fit_residuals) < 180:
        fit_residuals = residuals
    offsets = [percentile(fit_residuals, q) for q in (0.02, 0.08, 0.16, 0.28, 0.42, 0.58, 0.72, 0.84, 0.92, 0.98)]
    fit_mean = statistics.mean(fit_ys)
    ss_total = sum((y - fit_mean) ** 2 for y in fit_ys)
    ss_residual = sum((y - (intercept + slope * x)) ** 2 for x, y in zip(fit_xs, fit_ys))
    r_squared = 1 - (ss_residual / ss_total) if ss_total else 0.0
    points = []
    for i, row in enumerate(rows):
        point: dict[str, object] = {
            "date": row["date"],
            "close": round(as_float(row["close"]), 2),
            "trend": round(math.exp(log_trends[i]), 2),
            "residual": round(residuals[i], 4),
            "zone": rainbow_zone(residuals[i], offsets),
        }
        for level, offset in enumerate(offsets):
            point[f"level_{level}"] = round(math.exp(log_trends[i] + offset), 2)
        points.append(point)
    latest = points[-1]
    latest_levels = [as_float(latest[f"level_{i}"]) for i in range(len(offsets))]
    return {
        "model": {
            "formula": "ln(price) = intercept + slope * ln(days_since_first_price)",
            "intercept": intercept,
            "slope": slope,
            "fit_start_date": fit_start,
            "r_squared": round(r_squared, 4),
            "residual_offsets": [round(o, 4) for o in offsets],
            "method": "Dynamic power-law regression with colored bands derived from historical residual percentiles.",
            "warning": "Rainbow bands are a historical visualization, not investment advice or a predictive model.",
        },
        "bands": [{"label": label, "color": color, "lower_level": i, "upper_level": i + 1} for i, (label, color) in enumerate(RAINBOW_BANDS)],
        "latest": {
            "date": latest["date"],
            "close": latest["close"],
            "trend": latest["trend"],
            "zone": latest["zone"],
            "residual": latest["residual"],
            "lower_band": max((v for v in latest_levels if v <= as_float(latest["close"])), default=latest_levels[0]),
            "upper_band": min((v for v in latest_levels if v >= as_float(latest["close"])), default=latest_levels[-1]),
        },
        "points": points,
    }


def detect_swings(rows: list[dict[str, object]], reversal_pct: float = 0.13) -> list[dict[str, object]]:
    if not rows:
        return []
    pivots: list[dict[str, object]] = [{"date": rows[0]["date"], "price": round(as_float(rows[0]["close"]), 2), "type": "low", "strength": 0.0}]
    base_price = as_float(rows[0]["close"])
    trend: str | None = None
    extreme_index = 0
    extreme_price = base_price
    for i, row in enumerate(rows[1:], start=1):
        price = as_float(row["close"])
        if trend is None:
            if price >= base_price * (1 + reversal_pct):
                trend = "up"; extreme_index = i; extreme_price = price
            elif price <= base_price * (1 - reversal_pct):
                pivots[0]["type"] = "high"; trend = "down"; extreme_index = i; extreme_price = price
            continue
        if trend == "up":
            if price >= extreme_price:
                extreme_index = i; extreme_price = price
            elif price <= extreme_price * (1 - reversal_pct):
                pivots.append({"date": rows[extreme_index]["date"], "price": round(extreme_price, 2), "type": "high", "strength": round(abs(extreme_price / as_float(pivots[-1]["price"]) - 1), 4)})
                trend = "down"; extreme_index = i; extreme_price = price
        else:
            if price <= extreme_price:
                extreme_index = i; extreme_price = price
            elif price >= extreme_price * (1 + reversal_pct):
                pivots.append({"date": rows[extreme_index]["date"], "price": round(extreme_price, 2), "type": "low", "strength": round(abs(extreme_price / as_float(pivots[-1]["price"]) - 1), 4)})
                trend = "up"; extreme_index = i; extreme_price = price
    if trend is not None and rows[extreme_index]["date"] != pivots[-1]["date"]:
        pivots.append({"date": rows[extreme_index]["date"], "price": round(extreme_price, 2), "type": "high" if trend == "up" else "low", "strength": round(abs(extreme_price / as_float(pivots[-1]["price"]) - 1), 4)})
    return pivots


def confluence_score(latest: dict[str, object], pivots: list[dict[str, object]]) -> tuple[int, dict[str, dict[str, object]]]:
    components: dict[str, dict[str, object]] = {}
    score = 0
    z = as_float(latest.get("z_score", 0))
    log_score = 2 if z <= -1.5 else 1 if z <= -0.5 else -2 if z >= 1.5 else 0
    components["log_regression"] = {"score": log_score, "detail": f"log z-score {z:.2f}"}; score += log_score
    rsi_value = latest.get("rsi_14d")
    rsi_score = 0
    rsi_detail = "RSI unavailable"
    if rsi_value is not None:
        rv = as_float(rsi_value)
        rsi_score = 1 if rv < 35 else -1 if rv > 70 else 0
        rsi_detail = f"{'washed-out' if rv < 35 else 'hot' if rv > 70 else 'neutral'} RSI {rv:.1f}"
    components["rsi"] = {"score": rsi_score, "detail": rsi_detail}; score += rsi_score
    mvrv_value = latest.get("latest_available_mvrv") or latest.get("mvrv")
    mvrv_score = 0
    mvrv_detail = "MVRV unavailable for this asset"
    if mvrv_value is not None:
        mv = as_float(mvrv_value)
        mvrv_score = 1 if mv < 1.8 else -1 if mv > 3.5 else 0
        mvrv_detail = f"MVRV {mv:.2f}"
    components["mvrv"] = {"score": mvrv_score, "detail": mvrv_detail}; score += mvrv_score
    fib_score = 0
    fib_detail = "need more swings for Fibonacci scoring"
    if len(pivots) >= 3:
        prev = as_float(pivots[-3]["price"]); high = as_float(pivots[-2]["price"]); low = as_float(pivots[-1]["price"])
        if high > prev and low < high:
            retrace = (high - low) / max(high - prev, 1e-9)
            fib_score = 1 if min(abs(retrace - t) for t in [0.382, 0.5, 0.618, 0.786]) <= 0.05 else 0
            fib_detail = f"latest pullback retraced {retrace:.2f} of prior upswing"
    components["fib"] = {"score": fib_score, "detail": fib_detail}; score += fib_score
    ma200 = latest.get("ma_200d")
    trend_score = 1 if ma200 is not None and as_float(latest["close"]) > as_float(ma200) else -1
    components["trend"] = {"score": trend_score, "detail": "above 200D MA" if trend_score > 0 else "below 200D MA or unavailable"}; score += trend_score
    return score, components


def build_elliott_wave(points: list[dict[str, object]], asset_name: str) -> dict[str, object]:
    swings = detect_swings(points, reversal_pct=0.13)
    visible_pivots = swings[-11:]
    latest = dict(points[-1])
    score, confluence = confluence_score(latest, swings)
    close = as_float(latest["close"])
    last_low = next((p for p in reversed(swings) if p["type"] == "low"), None)
    last_high = next((p for p in reversed(swings) if p["type"] == "high"), None)
    invalidation = round(as_float(last_low["price"]) * 0.985, 2) if last_low else round(close * 0.85, 2)
    confirmation = round(as_float(last_high["price"]) * 1.01, 2) if last_high else round(close * 1.15, 2)
    base_low = as_float(last_low["price"]) if last_low else close
    swing_range = max((as_float(last_high["price"]) - base_low) if last_high else close * 0.2, close * 0.1)
    targets = [round(base_low + swing_range * m, 2) for m in (0.618, 1.0, 1.618)]
    confidence = max(0.05, min(0.9, 0.45 + (score * 0.07)))
    return {
        "version": "v1+phase2",
        "mode": "algorithmic_with_manual_override_available",
        "method": "13% ZigZag pivots, rule-based primary/alternate scenarios, and Phase 2 confluence scoring.",
        "pivots": visible_pivots,
        "primary": {
            "label": f"Primary {asset_name} bullish reset / possible Wave 4 to Wave 5 setup" if score >= 1 else f"Primary {asset_name} cautious count / correction still active",
            "structure": "Potential impulse/correction path from recent pivots. Scenario, not gospel from Chart Olympus.",
            "status": "candidate-rule-based-not-advice",
            "confidence": round(confidence, 2),
            "current_wave": "possible Wave 4 base or early Wave 5 confirmation watch" if score >= 1 else "possible ABC correction or unfinished Wave 4",
            "invalidation_level_usd": invalidation,
            "confirmation_level_usd": confirmation,
            "target_zones_usd": targets,
            "notes": [str(item["detail"]) for item in confluence.values()] + ["Close above confirmation improves the bullish count; break below invalidation promotes alternate."],
        },
        "alternate": {
            "label": "Alternate ABC correction / deeper reset",
            "structure": "A-B-C corrective path remains live until price reclaims confirmation and trend support.",
            "status": "alternate-risk-scenario",
            "confidence": round(max(0.05, 1 - confidence), 2),
            "invalidation_level_usd": confirmation,
            "confirmation_level_usd": invalidation,
            "target_zones_usd": [round(invalidation * 0.88, 2), round(invalidation * 0.80, 2)],
            "notes": ["This is a risk map, not an execution signal."],
        },
        "phase2_confluence": confluence,
        "confluence_score": score,
        "limitations": ["V1 generates scenarios from pivots; manual review still wins when the robot starts cosplaying Nostradamus."],
    }


def score_latest(latest: dict[str, object]) -> tuple[int, list[dict[str, object]], str]:
    components: list[dict[str, object]] = []
    total = 0
    z = as_float(latest["z_score"])
    val_score = 3 if z <= -2 else 2 if z <= -1.5 else 1 if z <= -0.5 else -3 if z >= 2 else -2 if z >= 1.5 else 0
    components.append({"name": "Log regression valuation", "score": val_score, "detail": f"z-score {z:.2f}"}); total += val_score
    close = as_float(latest["close"])
    ma200 = latest.get("ma_200d")
    trend_score = 1 if ma200 is not None and close > as_float(ma200) else -1
    components.append({"name": "200D trend", "score": trend_score, "detail": "above 200D MA" if trend_score > 0 else "below 200D MA or unavailable"}); total += trend_score
    rsi14 = latest.get("rsi_14d")
    rsi_score = 0; rsi_detail = "not enough data"
    if rsi14 is not None:
        rv = as_float(rsi14); rsi_score = 1 if rv < 35 else -1 if rv > 70 else 0; rsi_detail = f"{'washed out' if rv < 35 else 'hot' if rv > 70 else 'neutral'} RSI {rv:.1f}"
    components.append({"name": "RSI momentum", "score": rsi_score, "detail": rsi_detail}); total += rsi_score
    dd = as_float(latest["drawdown_from_ath_pct"])
    dd_score = 2 if dd <= -60 else 1 if dd <= -35 else -1 if dd >= -10 else 0
    components.append({"name": "Drawdown reset", "score": dd_score, "detail": f"{dd:.1f}% from ATH"}); total += dd_score
    mvrv = latest.get("latest_available_mvrv") or latest.get("mvrv")
    mvrv_score = 0; mvrv_detail = "not available for this asset"
    if mvrv is not None:
        mv = as_float(mvrv); mvrv_score = 2 if mv < 1 else 1 if mv < 1.8 else -2 if mv > 5 else -1 if mv > 3.5 else 0; mvrv_detail = f"MVRV {mv:.2f}"
    components.append({"name": "MVRV valuation", "score": mvrv_score, "detail": mvrv_detail}); total += mvrv_score
    label = "Strong accumulation / bullish regime" if total >= 5 else "Constructive" if total >= 2 else "Neutral / wait" if total >= -1 else "Risk-off" if total >= -4 else "High-risk / overheated"
    return total, components, label


def build_asset(asset: dict[str, str]) -> dict[str, object]:
    rows = read_rows(asset["id"])
    first_dt = datetime.fromisoformat(str(rows[0]["date"])).date()
    closes = [as_float(r["close"]) for r in rows]
    xs = []
    ys = []
    for row in rows:
        dt = datetime.fromisoformat(str(row["date"])).date()
        days = max((dt - first_dt).days + 1, 1)
        xs.append(math.log(days)); ys.append(math.log(as_float(row["close"])))
    fit_start = asset["fit_start"]
    fit_mask = date_mask(rows, fit_start)
    if sum(fit_mask) < 180:
        fit_start = str(rows[0]["date"])
        fit_mask = [True] * len(rows)
    fit_xs = [x for x, include in zip(xs, fit_mask) if include]
    fit_ys = [y for y, include in zip(ys, fit_mask) if include]
    intercept, slope = linreg(fit_xs, fit_ys)
    log_trends = [intercept + slope * x for x in xs]
    residuals = [y - t for y, t in zip(ys, log_trends)]
    fit_residuals = [r for r, include in zip(residuals, fit_mask) if include]
    std = statistics.pstdev(fit_residuals)
    if std == 0:
        std = statistics.pstdev(residuals) or 1
    ma_50 = moving_average(closes, 50); ma_100 = moving_average(closes, 100); ma_111 = moving_average(closes, 111); ma_200 = moving_average(closes, 200); ma_200w = weekly_moving_average(rows, closes, 200); ma_350 = moving_average(closes, 350); rsi_14 = rsi(closes, 14)
    ath = 0.0
    points: list[dict[str, object]] = []
    for i, row in enumerate(rows):
        close = closes[i]; ath = max(ath, close); z = residuals[i] / std
        points.append({
            "date": row["date"], "close": round(close, 2), "trend": round(math.exp(log_trends[i]), 2),
            "band_minus_2": round(math.exp(log_trends[i] - 2 * std), 2), "band_minus_1_5": round(math.exp(log_trends[i] - 1.5 * std), 2), "band_minus_1": round(math.exp(log_trends[i] - std), 2),
            "band_plus_1": round(math.exp(log_trends[i] + std), 2), "band_plus_2": round(math.exp(log_trends[i] + 2 * std), 2),
            "z_score": round(z, 4), "zone": zone_from_z(z),
            "ma_50d": rounded_optional(ma_50[i]), "ma_100d": rounded_optional(ma_100[i]), "ma_111d": rounded_optional(ma_111[i]), "ma_200d": rounded_optional(ma_200[i]), "ma_200w": rounded_optional(ma_200w[i]), "ma_350d_x2": round(as_float(ma_350[i]) * 2, 2) if ma_350[i] is not None else None,
            "rsi_14d": rounded_optional(rsi_14[i]), "drawdown_from_ath_pct": round((close / ath - 1) * 100, 2),
            "mvrv": rounded_object(row.get("mvrv")), "market_cap_usd": rounded_object(row.get("market_cap_usd")), "realized_cap_usd": rounded_object(row.get("realized_cap_usd")),
        })
    latest = points[-1]
    latest_mvrv_point = next((p for p in reversed(points) if p.get("mvrv") is not None), None)
    latest_for_score = dict(latest)
    if latest.get("mvrv") is None and latest_mvrv_point is not None:
        latest_for_score["latest_available_mvrv"] = latest_mvrv_point["mvrv"]
    score, components, regime = score_latest(latest_for_score)
    meta_path = RAW_DIR / f"{asset['id']}.meta.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "asset": {"id": asset["id"], "name": asset["name"], "symbol": asset["symbol"], "price_label": asset["price_label"], "category": asset.get("category")},
        "model": {"formula": "ln(price) = intercept + slope * ln(days_since_first_price)", "intercept": intercept, "slope": slope, "residual_std_dev": std, "fit_start_date": fit_start, "band_calibration": "Residual standard deviation from asset-specific mature/history window."},
        "source": meta,
        "latest": {**latest, "zone_note": zone_note(str(latest["zone"]), asset["name"]), "distance_to_minus_1_5_pct": round((as_float(latest["close"]) / as_float(latest["band_minus_1_5"]) - 1) * 100, 2), "distance_to_plus_2_pct": round((as_float(latest["band_plus_2"]) / as_float(latest["close"]) - 1) * 100, 2), "latest_available_mvrv": latest_mvrv_point["mvrv"] if latest_mvrv_point else None, "latest_available_mvrv_date": latest_mvrv_point["date"] if latest_mvrv_point else None},
        "regime": {"score": score, "label": regime, "components": components, "scale": "rough MVP score, -10 to +10 target as more indicators are added"},
        "manual_thesis": {"primary_thesis": "Manual thesis not set", "alternate_thesis": "Manual thesis not set", "manual_elliott_wave_count": {"status": "Manual override available"}},
        "rainbow": build_rainbow(rows, xs, ys, fit_start),
        "elliott_wave": build_elliott_wave(points, asset["name"]),
        "points": points,
    }
    return payload


def main() -> int:
    index = []
    for asset in ASSETS:
        payload = build_asset(asset)
        out = PUBLIC_DIR / f"{asset['id']}.json"
        out.write_text(json.dumps(payload, indent=2))
        index.append({"id": asset["id"], "name": asset["name"], "symbol": asset["symbol"], "category": asset.get("category"), "url": f"/public/data/{asset['id']}.json", "latest": payload["latest"], "regime": payload["regime"], "source": payload["source"]})
    assets_index = {"generated_at": datetime.now(timezone.utc).isoformat(), "assets": index}
    (PUBLIC_DIR / "assets.json").write_text(json.dumps(assets_index, indent=2))
    print(json.dumps({"output_dir": str(PUBLIC_DIR), "assets": [{"id": a["id"], "close": a["latest"]["close"], "date": a["latest"]["date"]} for a in index]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
