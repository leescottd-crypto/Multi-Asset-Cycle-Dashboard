#!/usr/bin/env python3
"""Validate the public Bitcoin macro payloads before serving them."""
from __future__ import annotations

import json
import math
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MACRO_PATH = ROOT / "public" / "data" / "btc-macro.json"
SUPPLY_PATH = ROOT / "public" / "data" / "btc-market-supply.json"
CORE_METRICS = {
    "net_liquidity", "m2", "broad_dollar", "real_yield_10y", "nfci", "wti",
    "debt_held_public", "gross_debt", "fed_treasuries",
}


def fail(message: str) -> None:
    raise SystemExit(f"Macro validation failed: {message}")


def main() -> int:
    macro = json.loads(MACRO_PATH.read_text())
    supply = json.loads(SUPPLY_PATH.read_text())
    metrics = macro.get("metrics", {})
    missing = CORE_METRICS - set(metrics)
    if missing:
        fail(f"missing core metrics: {sorted(missing)}")

    for key in CORE_METRICS:
        metric = metrics[key]
        rows = metric.get("series", [])
        if not rows:
            fail(f"{key} has no observations")
        if str(rows[0]["date"]) > "2016-01-01":
            fail(f"{key} does not provide a ten-year view")
        dates = [str(row["date"]) for row in rows]
        if dates != sorted(set(dates)):
            fail(f"{key} dates are not sorted and unique")
        if any(not math.isfinite(float(row["value"])) for row in rows):
            fail(f"{key} contains a non-finite value")
        for required in ("source", "source_url", "cadence", "unit", "date"):
            if not metric.get(required):
                fail(f"{key} is missing {required}")

    net_liquidity = float(metrics["net_liquidity"]["value"])
    if not 1_000 <= net_liquidity <= 15_000:
        fail(f"net-liquidity units are implausible: {net_liquidity} USD billions")

    holders = macro.get("holders", {}).get("holders", [])
    if len(holders) < 10:
        fail("fewer than ten foreign Treasury holders")
    for holder in holders:
        if len(holder.get("series", [])) < 120:
            fail(f"{holder.get('country')} lacks ten years of monthly holder history")
        if holder.get("value", 0) < 0:
            fail(f"{holder.get('country')} has negative holdings")

    if supply.get("status") not in {"live", "provider_required"}:
        fail("unexpected BTC market-supply status")
    if not supply.get("warning"):
        fail("BTC market-supply caveat is absent")

    print(json.dumps({
        "valid": True,
        "core_metrics": len(CORE_METRICS),
        "foreign_holders": len(holders),
        "exchange_supply_status": supply["status"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
