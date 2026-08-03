#!/usr/bin/env python3
"""Fetch official long-history macro and U.S. Treasury-holder data.

Paid crypto-market providers are optional. If a Glassnode key is absent, the
macro dashboard still builds and exposes an explicit provider-required state.
"""
from __future__ import annotations

import csv
import io
import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw" / "macro"
USER_AGENT = "Mozilla/5.0 multi-asset-cycle-dashboard/0.3"
FRED_SERIES = {
    "walcl": "WALCL",
    "tga": "WTREGEN",
    "rrp": "RRPONTSYD",
    "broad_dollar": "DTWEXBGS",
    "real_yield_10y": "DFII10",
    "nfci": "NFCI",
    "m2": "M2SL",
    "fed_treasuries": "TREAST",
    "wti": "DCOILWTICO",
    "credit_spread": "BAA10Y",
}
FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
DEBT_URL = (
    "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v2/"
    "accounting/od/debt_to_penny?filter=record_date:gte:2014-01-01"
    "&page[size]=10000&sort=record_date"
)
TIC_HISTORY_URL = "https://ticdata.treasury.gov/resource-center/data-chart-center/tic/Documents/mfhhis01.txt"
TIC_LATEST_URL = "https://ticdata.treasury.gov/resource-center/data-chart-center/tic/Documents/slt_table5.txt"
GLASSNODE_URL = "https://api.glassnode.com/v1/metrics/distribution/{metric}"
STABLECOIN_URL = "https://stablecoins.llama.fi/stablecoincharts/all"


def fetch_text(url: str, timeout: int = 60) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        if response.status != 200:
            raise RuntimeError(f"HTTP {response.status}: {url}")
        return response.read().decode("utf-8-sig", "replace")


def fetch_json(url: str, timeout: int = 60) -> dict[str, Any] | list[Any]:
    return json.loads(fetch_text(url, timeout))


def write_json(name: str, payload: Any) -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    (RAW_DIR / name).write_text(json.dumps(payload, indent=2) + "\n")


def parse_fred(text: str) -> list[dict[str, float | str]]:
    rows: list[dict[str, float | str]] = []
    for row in csv.DictReader(io.StringIO(text)):
        value_key = next((key for key in row if key != "observation_date"), None)
        raw = row.get(value_key, "") if value_key else ""
        try:
            value = float(raw)
        except (TypeError, ValueError):
            continue
        rows.append({"date": row["observation_date"], "value": value})
    return rows


def numeric_values(fields: list[str]) -> list[float]:
    values: list[float] = []
    for field in fields:
        cleaned = field.strip().replace(",", "")
        if cleaned in {"", "--", "n.a.", "*"}:
            continue
        try:
            values.append(float(cleaned))
        except ValueError:
            break
    return values


def parse_tic_history(text: str) -> dict[str, list[dict[str, float | str]]]:
    """Parse Treasury's year-block MFH history (columns are Dec through Jan)."""
    lines = list(csv.reader(io.StringIO(text), delimiter="\t"))
    output: dict[str, list[dict[str, float | str]]] = {}
    for index, fields in enumerate(lines):
        if not fields or fields[0].strip() != "Country":
            continue
        years = [field.strip() for field in fields[1:] if field.strip().isdigit()]
        if not years:
            continue
        year = int(years[0])
        row_index = index + 1
        while row_index < len(lines):
            row = lines[row_index]
            name = row[0].strip().strip('"') if row else ""
            if not name or name.startswith("-") or name == "Country":
                row_index += 1
                if name == "Country":
                    break
                continue
            values = numeric_values(row[1:])
            if not values:
                if name.startswith(("1/", "2/", "Note", "Grand Total")):
                    break
                row_index += 1
                continue
            for position, value in enumerate(values[:12]):
                month = 12 - position
                output.setdefault(name, []).append(
                    {"date": f"{year:04d}-{month:02d}-01", "value": value}
                )
            row_index += 1
    return output


def parse_tic_latest(text: str) -> dict[str, list[dict[str, float | str]]]:
    lines = list(csv.reader(io.StringIO(text), delimiter="\t"))
    header_index = next(i for i, row in enumerate(lines) if row and row[0].strip() == "Country")
    dates = [value.strip() for value in lines[header_index][1:] if value.strip()]
    output: dict[str, list[dict[str, float | str]]] = {}
    for row in lines[header_index + 1:]:
        if not row or not row[0].strip():
            continue
        name = row[0].strip().strip('"')
        values = numeric_values(row[1:])
        if not values:
            continue
        output[name] = [
            {"date": f"{date}-01", "value": value}
            for date, value in zip(dates, values)
        ]
    return output


def merge_tic(
    history: dict[str, list[dict[str, float | str]]],
    latest: dict[str, list[dict[str, float | str]]],
) -> dict[str, list[dict[str, float | str]]]:
    merged: dict[str, list[dict[str, float | str]]] = {}
    for country in set(history) | set(latest):
        by_date = {
            str(row["date"]): float(row["value"])
            for row in history.get(country, []) + latest.get(country, [])
        }
        merged[country] = [
            {"date": date, "value": value}
            for date, value in sorted(by_date.items())
        ]
    return merged


def fetch_glassnode(api_key: str) -> dict[str, Any]:
    metrics = {
        "exchange_balance": "balance_exchanges",
        "exchange_balance_relative": "balance_exchanges_relative",
        "exchange_net_position_change": "exchange_net_position_change",
    }
    result: dict[str, Any] = {}
    for name, metric in metrics.items():
        query = urllib.parse.urlencode({"a": "BTC", "i": "24h", "api_key": api_key})
        url = f"{GLASSNODE_URL.format(metric=metric)}?{query}"
        data = fetch_json(url)
        result[name] = [
            {
                "date": datetime.fromtimestamp(int(row["t"]), timezone.utc).date().isoformat(),
                "value": float(row["v"]),
            }
            for row in data
        ]
    return result


def main() -> int:
    fetched_at = datetime.now(timezone.utc).isoformat()
    errors: list[str] = []

    for name, series_id in FRED_SERIES.items():
        url = FRED_URL.format(series_id=series_id)
        try:
            rows = parse_fred(fetch_text(url))
            if not rows:
                raise RuntimeError("no observations")
            write_json(f"fred-{name}.json", {
                "series_id": series_id,
                "source": "Federal Reserve Bank of St. Louis (FRED)",
                "source_url": url,
                "fetched_at": fetched_at,
                "observations": rows,
            })
        except Exception as exc:
            errors.append(f"FRED {series_id}: {exc}")

    try:
        debt_payload = fetch_json(DEBT_URL)
        write_json("treasury-debt.json", {
            "source": "U.S. Treasury FiscalData - Debt to the Penny",
            "source_url": DEBT_URL,
            "fetched_at": fetched_at,
            "observations": debt_payload.get("data", []),
        })
    except Exception as exc:
        errors.append(f"Treasury debt: {exc}")

    try:
        history = parse_tic_history(fetch_text(TIC_HISTORY_URL))
        latest = parse_tic_latest(fetch_text(TIC_LATEST_URL))
        countries = merge_tic(history, latest)
        write_json("treasury-foreign-holders.json", {
            "source": "U.S. Treasury International Capital - Major Foreign Holders",
            "source_url": TIC_LATEST_URL,
            "history_url": TIC_HISTORY_URL,
            "fetched_at": fetched_at,
            "unit": "USD billions",
            "methodology_warning": (
                "TIC country attribution is primarily custodial. The reported country may be "
                "a financial center or custodian rather than the ultimate beneficial owner."
            ),
            "countries": countries,
        })
    except Exception as exc:
        errors.append(f"Treasury foreign holders: {exc}")

    try:
        stablecoins = fetch_json(STABLECOIN_URL)
        observations = []
        today = datetime.now(timezone.utc).date()
        for row in stablecoins:
            date = datetime.fromtimestamp(int(row["date"]), timezone.utc).date()
            value = row.get("totalCirculatingUSD", {}).get("peggedUSD")
            if date <= today and value is not None and float(value) > 0:
                observations.append({"date": date.isoformat(), "value": float(value)})
        write_json("stablecoin-supply.json", {
            "source": "DefiLlama Stablecoins",
            "source_url": STABLECOIN_URL,
            "fetched_at": fetched_at,
            "unit": "USD",
            "history_class": "Tactical / shorter history",
            "observations": observations,
        })
    except Exception as exc:
        errors.append(f"Stablecoin supply: {exc}")

    api_key = os.environ.get("GLASSNODE_API_KEY", "").strip()
    if api_key:
        try:
            write_json("glassnode-exchange-supply.json", {
                "source": "Glassnode",
                "source_url": "https://docs.glassnode.com/basic-api/endpoints/distribution",
                "fetched_at": fetched_at,
                "observations": fetch_glassnode(api_key),
            })
        except Exception as exc:
            errors.append(f"Glassnode: {exc}")
    else:
        errors.append("Glassnode exchange supply: GLASSNODE_API_KEY is not configured")

    write_json("fetch-status.json", {"fetched_at": fetched_at, "errors": errors})
    print(json.dumps({"raw_dir": str(RAW_DIR), "errors": errors}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
