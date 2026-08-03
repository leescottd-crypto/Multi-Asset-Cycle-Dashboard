#!/usr/bin/env python3
"""Build compact UI payloads for the Bitcoin macro workspace."""
from __future__ import annotations

import json
import math
from bisect import bisect_right
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw" / "macro"
PUBLIC_DIR = ROOT / "public" / "data"
START_DATE = "2014-01-01"
CONFIG = json.loads((ROOT / "data" / "manual" / "macro-config.json").read_text())
HOLDER_LIMIT = int(CONFIG["foreign_holders"]["show_top"])
HOLDER_3M_THRESHOLD = float(CONFIG["foreign_holders"]["buying_threshold_3m_usd_billions"])
HOLDER_12M_THRESHOLD = float(CONFIG["foreign_holders"]["buying_threshold_12m_usd_billions"])
FINANCIAL_CENTERS = {
    "Belgium", "Cayman Islands", "Ireland", "Luxembourg", "Singapore",
    "Switzerland", "United Kingdom", "Hong Kong", "Bermuda",
}
AGGREGATE_COUNTRIES = {
    "All Other", "Grand Total", "For. Official", "Treasury Bills", "T-Bonds & Notes",
    "Of Which: Foreign Official", "Of Which: Foreign Official Treasury Bills",
    "Of Which: Foreign Official T-Bonds & Notes", "Oil Exporters",
    "Caribbean Banking Centers", "Euro Area", "Middle East Oil Exporters",
}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text())


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n")


def clean_series(rows: list[dict[str, Any]], scale: float = 1.0) -> list[dict[str, float | str]]:
    output = []
    for row in rows:
        try:
            value = float(row["value"]) * scale
        except (KeyError, TypeError, ValueError):
            continue
        if math.isfinite(value) and str(row["date"]) >= START_DATE:
            output.append({"date": str(row["date"])[:10], "value": round(value, 6)})
    return sorted(output, key=lambda row: str(row["date"]))


def monthly_last(rows: list[dict[str, float | str]]) -> list[dict[str, float | str]]:
    months: dict[str, dict[str, float | str]] = {}
    for row in rows:
        months[str(row["date"])[:7]] = row
    return list(months.values())


def value_before(rows: list[dict[str, float | str]], target: str) -> float | None:
    dates = [str(row["date"]) for row in rows]
    index = bisect_right(dates, target) - 1
    return float(rows[index]["value"]) if index >= 0 else None


def months_before(date_string: str, months: int) -> str:
    current = date.fromisoformat(date_string[:10])
    year = current.year
    month = current.month - months
    while month <= 0:
        year -= 1
        month += 12
    return f"{year:04d}-{month:02d}-{min(current.day, 28):02d}"


def change(rows: list[dict[str, float | str]], months: int, percent: bool = False) -> float | None:
    if not rows:
        return None
    current = float(rows[-1]["value"])
    prior = value_before(rows, months_before(str(rows[-1]["date"]), months))
    if prior is None:
        return None
    result = (current / prior - 1) * 100 if percent and prior else current - prior
    return round(result, 2)


def percentile(rows: list[dict[str, float | str]], current: float | None = None) -> float | None:
    values = [float(row["value"]) for row in rows if str(row["date"]) >= "2015-01-01"]
    if not values:
        return None
    latest = values[-1] if current is None else current
    return round(100 * sum(value <= latest for value in values) / len(values), 1)


def latest_at(primary_dates: list[str], rows: list[dict[str, float | str]]) -> list[float | None]:
    dates = [str(row["date"]) for row in rows]
    values = [float(row["value"]) for row in rows]
    output: list[float | None] = []
    for current in primary_dates:
        index = bisect_right(dates, current) - 1
        output.append(values[index] if index >= 0 else None)
    return output


def metric(
    key: str,
    label: str,
    rows: list[dict[str, float | str]],
    unit: str,
    cadence: str,
    source: str,
    source_url: str,
    supportive_when: str,
    caveat: str = "",
) -> dict[str, Any]:
    latest = rows[-1] if rows else None
    return {
        "key": key,
        "label": label,
        "value": latest["value"] if latest else None,
        "date": latest["date"] if latest else None,
        "unit": unit,
        "change_3m": change(rows, 3),
        "change_12m": change(rows, 12),
        "change_3m_pct": change(rows, 3, True),
        "change_12m_pct": change(rows, 12, True),
        "percentile_since_2015": percentile(rows),
        "cadence": cadence,
        "source": source,
        "source_url": source_url,
        "supportive_when": supportive_when,
        "caveat": caveat,
        "series": monthly_last(rows),
    }


def fred(name: str, scale: float = 1.0) -> tuple[list[dict[str, float | str]], dict[str, Any]]:
    payload = read_json(RAW_DIR / f"fred-{name}.json")
    return clean_series(payload["observations"], scale), payload


def build_net_liquidity(
    walcl: list[dict[str, float | str]],
    tga: list[dict[str, float | str]],
    rrp: list[dict[str, float | str]],
) -> list[dict[str, float | str]]:
    dates = [str(row["date"]) for row in walcl]
    tga_values = latest_at(dates, tga)
    rrp_values = latest_at(dates, rrp)
    output = []
    for row, tga_value, rrp_value in zip(walcl, tga_values, rrp_values):
        if tga_value is None or rrp_value is None:
            continue
        output.append({
            "date": row["date"],
            "value": round(float(row["value"]) - tga_value - rrp_value, 3),
        })
    return output


def trend_label(delta: float | None, threshold: float = 0.0) -> str:
    if delta is None:
        return "unavailable"
    if delta > threshold:
        return "buying"
    if delta < -threshold:
        return "selling"
    return "roughly flat"


def build_holders() -> dict[str, Any]:
    payload = read_json(RAW_DIR / "treasury-foreign-holders.json")
    countries = {}
    for country, raw_rows in payload["countries"].items():
        rows = clean_series(raw_rows)
        if (
            country not in AGGREGATE_COUNTRIES
            and not country.startswith("Of which")
            and not country.startswith("Of Which")
            and rows
        ):
            countries[country] = rows
    ranked = sorted(countries.items(), key=lambda item: float(item[1][-1]["value"]), reverse=True)[:HOLDER_LIMIT]
    total_series = clean_series(payload["countries"].get("Grand Total", []))
    total_latest = float(total_series[-1]["value"]) if total_series else None
    holders = []
    for country, rows in ranked:
        latest = float(rows[-1]["value"])
        delta_3m = change(rows, 3)
        delta_12m = change(rows, 12)
        holders.append({
            "country": country,
            "value": latest,
            "date": rows[-1]["date"],
            "share_foreign_pct": round(latest / total_latest * 100, 2) if total_latest else None,
            "change_3m": delta_3m,
            "change_12m": delta_12m,
            "trend_3m": trend_label(delta_3m, HOLDER_3M_THRESHOLD),
            "trend_12m": trend_label(delta_12m, HOLDER_12M_THRESHOLD),
            "custody_center": country in FINANCIAL_CENTERS,
            "series": monthly_last(rows),
        })
    return {
        "as_of": max((holder["date"] for holder in holders), default=None),
        "unit": "USD billions",
        "total_foreign": total_latest,
        "holders": holders,
        "source": payload["source"],
        "source_url": payload["source_url"],
        "history_url": payload["history_url"],
        "methodology_warning": payload["methodology_warning"],
    }


def build_debt() -> tuple[list[dict[str, float | str]], list[dict[str, float | str]], dict[str, Any]]:
    payload = read_json(RAW_DIR / "treasury-debt.json")
    held_public = []
    gross = []
    for row in payload["observations"]:
        try:
            held_public.append({"date": row["record_date"], "value": float(row["debt_held_public_amt"]) / 1e12})
            gross.append({"date": row["record_date"], "value": float(row["tot_pub_debt_out_amt"]) / 1e12})
        except (KeyError, TypeError, ValueError):
            continue
    return monthly_last(held_public), monthly_last(gross), payload


def build_market_supply() -> dict[str, Any]:
    stablecoin_path = RAW_DIR / "stablecoin-supply.json"
    stablecoins = None
    if stablecoin_path.exists():
        stable_payload = read_json(stablecoin_path)
        stable_rows = clean_series(stable_payload.get("observations", []), 1 / 1e9)
        stablecoins = metric(
            "stablecoin_supply", "USD Stablecoin Supply", stable_rows, "USD billions", "daily",
            stable_payload["source"], stable_payload["source_url"], "rising supply is generally supportive",
            "Shorter history; stablecoin supply is potential crypto liquidity, not committed BTC demand.",
        )

    glassnode_path = RAW_DIR / "glassnode-exchange-supply.json"
    exchange_metrics = []
    status = "provider_required"
    status_message = "Add GLASSNODE_API_KEY to populate labelled exchange inventory and net-flow history."
    if glassnode_path.exists():
        glassnode = read_json(glassnode_path)
        observations = glassnode.get("observations", {})
        specs = [
            ("exchange_balance", "BTC on Labelled Exchanges", "BTC", 1.0, "falling inventory is generally supportive"),
            ("exchange_balance_relative", "Exchange Balance / BTC Supply", "%", 100.0, "falling share is generally supportive"),
            ("exchange_net_position_change", "30D Exchange Net Position", "BTC", 1.0, "negative values indicate net outflow"),
        ]
        for key, label, unit, scale, supportive in specs:
            rows = clean_series(observations.get(key, []), scale)
            if rows:
                exchange_metrics.append(metric(
                    key, label, rows, unit, "daily", glassnode["source"], glassnode["source_url"], supportive,
                    "Labelled-address estimates can be revised; exchange custody inventory is not an order book.",
                ))
        if exchange_metrics:
            status = "live"
            status_message = "Labelled exchange inventory and flows are available."

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "status_message": status_message,
        "exchange_metrics": exchange_metrics,
        "stablecoin": stablecoins,
        "order_book": {
            "status": "provider_required",
            "message": "Historical ask-side depth within 1% and 2% requires a market-data provider such as Kaiko or Coin Metrics.",
        },
        "warning": "Exchange custody inventory is not equivalent to coins offered for sale.",
    }


def main() -> int:
    walcl, walcl_meta = fred("walcl", 1 / 1000)
    tga, tga_meta = fred("tga", 1 / 1000)
    rrp, rrp_meta = fred("rrp")
    dollar, dollar_meta = fred("broad_dollar")
    real_yield, real_yield_meta = fred("real_yield_10y")
    nfci, nfci_meta = fred("nfci")
    m2, m2_meta = fred("m2")
    fed_treasuries, fed_treasuries_meta = fred("fed_treasuries", 1 / 1000)
    oil, oil_meta = fred("wti")
    credit, credit_meta = fred("credit_spread")
    net_liquidity = build_net_liquidity(walcl, tga, rrp)
    held_public, gross_debt, debt_meta = build_debt()
    holders = build_holders()
    market_supply = build_market_supply()

    metrics = {
        "net_liquidity": metric(
            "net_liquidity", "Net Liquidity Proxy", net_liquidity, "USD billions", "weekly",
            "Federal Reserve / U.S. Treasury via FRED", walcl_meta["source_url"], "rising is generally supportive",
            "Federal Reserve assets minus Treasury cash minus overnight reverse repos; this is a proxy, not an official measure.",
        ),
        "m2": metric("m2", "U.S. M2", m2, "USD billions", "monthly", m2_meta["source"], m2_meta["source_url"], "accelerating growth is generally supportive"),
        "broad_dollar": metric("broad_dollar", "Broad U.S. Dollar", dollar, "index", "daily", dollar_meta["source"], dollar_meta["source_url"], "falling is generally supportive"),
        "real_yield_10y": metric("real_yield_10y", "10Y Real Yield", real_yield, "%", "daily", real_yield_meta["source"], real_yield_meta["source_url"], "falling is generally supportive"),
        "nfci": metric("nfci", "Financial Conditions", nfci, "index", "weekly", nfci_meta["source"], nfci_meta["source_url"], "falling / negative is easier"),
        "wti": metric("wti", "WTI Oil", oil, "USD/barrel", "daily", oil_meta["source"], oil_meta["source_url"], "contained price shocks are generally supportive"),
        "credit_spread": metric("credit_spread", "Baa - 10Y Credit Spread", credit, "% points", "daily", credit_meta["source"], credit_meta["source_url"], "falling is generally supportive"),
        "debt_held_public": metric("debt_held_public", "Debt Held by the Public", held_public, "USD trillions", "daily", debt_meta["source"], debt_meta["source_url"], "context only"),
        "gross_debt": metric("gross_debt", "Gross Federal Debt", gross_debt, "USD trillions", "daily", debt_meta["source"], debt_meta["source_url"], "context only"),
        "fed_treasuries": metric("fed_treasuries", "Fed Treasury Holdings", fed_treasuries, "USD billions", "weekly", fed_treasuries_meta["source"], fed_treasuries_meta["source_url"], "rising holdings can absorb market supply"),
    }

    liquidity_score = sum([
        1 if (metrics["net_liquidity"]["change_3m"] or 0) > 0 else -1,
        1 if (metrics["m2"]["change_3m_pct"] or 0) > 0 else -1,
    ])
    rates_score = sum([
        1 if (metrics["broad_dollar"]["change_3m_pct"] or 0) < 0 else -1,
        1 if (metrics["real_yield_10y"]["change_3m"] or 0) < 0 else -1,
        1 if (metrics["nfci"]["change_3m"] or 0) < 0 else -1,
    ])
    foreign_delta = sum((holder["change_12m"] or 0) for holder in holders["holders"])
    fiscal_state = "foreign demand rising" if foreign_delta > 0 else "foreign demand falling"
    supply_state = "available" if market_supply["status"] == "live" else "provider needed"

    fetch_status_path = RAW_DIR / "fetch-status.json"
    fetch_status = read_json(fetch_status_path) if fetch_status_path.exists() else {"errors": []}
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "history_start": START_DATE,
        "pillars": [
            {"key": "liquidity", "label": "Dollar Liquidity", "state": "supportive" if liquidity_score > 0 else "restrictive" if liquidity_score < 0 else "mixed", "detail": "Net liquidity and M2 impulse"},
            {"key": "rates", "label": "Dollar & Rates", "state": "supportive" if rates_score > 0 else "restrictive" if rates_score < 0 else "mixed", "detail": "Dollar, real yields and financial conditions"},
            {"key": "fiscal", "label": "Fiscal Absorption", "state": fiscal_state, "detail": "Debt growth, Fed and foreign holders"},
            {"key": "supply", "label": "BTC Market Supply", "state": supply_state, "detail": "Exchange inventory, flows and stablecoins"},
        ],
        "metrics": metrics,
        "holders": holders,
        "market_supply_url": "/public/data/btc-market-supply.json",
        "refresh_errors": fetch_status.get("errors", []),
        "methodology": {
            "warning": "Macro relationships with Bitcoin are regime-dependent. These indicators are context, not causal trading signals.",
            "net_liquidity_formula": "Federal Reserve total assets - Treasury General Account - overnight reverse repos",
            "country_warning": holders["methodology_warning"],
        },
    }
    write_json(PUBLIC_DIR / "btc-macro.json", payload)
    write_json(PUBLIC_DIR / "btc-market-supply.json", market_supply)
    print(json.dumps({
        "macro_output": str(PUBLIC_DIR / "btc-macro.json"),
        "supply_output": str(PUBLIC_DIR / "btc-market-supply.json"),
        "holders": len(holders["holders"]),
        "supply_status": market_supply["status"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
