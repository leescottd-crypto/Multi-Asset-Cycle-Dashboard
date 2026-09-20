#!/usr/bin/env python3
"""Refresh market-size snapshots without substituting ETF prices for metal spot.

Crypto and metal spot are refreshed on each asset fetch. Other measures are
explicitly dated reference observations, updated in data/manual/market-sizes.json.
Failed providers retain the previous observation and its original date.
"""
import json
import math
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "public/data/market-sizes.json"
COINS = {"bitcoin": "btc", "ethereum": "eth", "solana": "sol", "sui": "sui", "hyperliquid": "hype"}
OZ_PER_TONNE = 32150.746568627
COIN_URL = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids=" + ",".join(COINS)


def request_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "MultiAssetDashboard/1.0"})
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.load(response)


def positive(value):
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or value <= 0:
        raise ValueError("Expected a positive finite market value")
    return value


def observation_date(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.date() > datetime.now(timezone.utc).date():
        raise ValueError("Future observation date")
    return parsed.date().isoformat()


def crypto_record(row):
    return {
        "label": "Market cap", "value_usd": positive(row["market_cap"]),
        "as_of": observation_date(row["last_updated"]),
        "source": "CoinGecko", "source_url": f"https://www.coingecko.com/en/coins/{row['id']}",
        "method": "Circulating-supply market capitalization in USD, not fully diluted valuation. Provider price timing may differ from the chart price.",
        "refresh_mode": "on asset refresh", "status": "ok",
    }


def metal_record(seed, quote):
    price = positive(quote["price"])
    quantity = positive(seed["stock_quantity"])
    ounces = quantity * OZ_PER_TONNE if seed["stock_unit"] == "tonnes" else quantity
    return {**seed, "value_usd": ounces * price, "as_of": observation_date(quote["updatedAt"]),
            "price_usd_per_oz": price, "price_source_url": f"https://api.gold-api.com/price/{quote['symbol']}",
            "refresh_mode": "spot on asset refresh; stock is a dated estimate", "status": "ok"}


def refresh_market_sizes(output=OUTPUT, fetch=request_json):
    seeds = json.loads((ROOT / "data/manual/market-sizes.json").read_text())
    previous = json.loads(output.read_text()).get("assets", {}) if output.exists() else {}
    records = {**previous, **seeds}
    errors = []

    def retain(asset_id, error):
        records[asset_id] = {**previous.get(asset_id, seeds.get(asset_id, {"label": "Market cap", "value_usd": None})),
                             "status": "refresh failed; retained observation"}
        errors.append(f"{asset_id}: {type(error).__name__}")

    try:
        rows = {row["id"]: row for row in fetch(COIN_URL)}
    except Exception as error:
        rows = {}
        errors.append(f"crypto feed: {type(error).__name__}")
    for coin_id, asset_id in COINS.items():
        try:
            records[asset_id] = crypto_record(rows[coin_id])
        except Exception as error:
            retain(asset_id, error)
    for asset_id, symbol in (("gold", "XAU"), ("silver", "XAG")):
        try:
            quote = fetch(f"https://api.gold-api.com/price/{symbol}")
            if quote.get("symbol") != symbol or quote.get("currency", "USD") != "USD":
                raise ValueError("Wrong metal or currency")
            records[asset_id] = metal_record(seeds[asset_id], quote)
        except Exception as error:
            retain(asset_id, error)
    payload = {"generated_at": datetime.now(timezone.utc).isoformat(), "assets": records, "errors": errors}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2) + "\n")
    return payload


if __name__ == "__main__":
    result = refresh_market_sizes()
    print(json.dumps({"assets": {key: {"value_usd": row.get("value_usd"), "as_of": row.get("as_of"), "status": row.get("status", "dated reference")} for key, row in result["assets"].items()}, "errors": result["errors"]}, indent=2))
