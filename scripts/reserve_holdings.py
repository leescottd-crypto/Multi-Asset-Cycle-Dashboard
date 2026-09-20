"""Build a dated reserve comparison; failures never replace the last good chart.

Gold input is a user-supplied WGC quarterly workbook, not an unattended feed.
Run with --gold-workbook PATH once (or for a newer release), then without it.
"""
import argparse
import calendar
import csv
import hashlib
import io
import json
import math
from datetime import datetime, timezone
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "data/manual/reserve-gold-world.json"
OUTPUT = ROOT / "public/data/reserve-holdings.json"
TIC = "https://ticdata.treasury.gov/resource-center/data-chart-center/tic/Documents/slt_table3.txt"
TIC_HISTORY = "https://ticdata.treasury.gov/resource-center/data-chart-center/tic/Documents/mfhhis01.txt"
CG = "https://api.coingecko.com/api/v3"
# Fixed coverage: no private officials, companies, municipal double-counts or
# inferred balances from seizure headlines. Provider estimates are not audits.
GOVERNMENTS = ["united-states", "united-kingdom", "el-salvador", "bhutan"]


def fetch(url):
    return subprocess.check_output([
        "curl", "--fail", "--silent", "--show-error", "--location",
        "--max-time", "40", url,
    ])


def quarter_end(label):
    q, year = label.split()
    month = int(q[1]) * 3
    return f"{year}-{month:02d}-{calendar.monthrange(int(year), month)[1]}"


def positive(value):
    return isinstance(value, (int, float)) and math.isfinite(value) and value > 0


def import_gold(path):
    import openpyxl
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    series = {}
    for name, key in [("Gold (US$ millions)", "gold_usd_m"),
                      ("Total Reserves (US$ millions)", "reserves_usd_m")]:
        rows = list(wb[name].values)
        matches = [(i, r) for i, r in enumerate(rows, 1) if r[0] == "World"]
        if len(matches) != 1:
            raise ValueError(f"Expected exactly one World row in {name}")
        row_number, world = matches[0]
        for col, label in enumerate(rows[1]):
            if isinstance(label, str) and label.startswith("Q"):
                if not positive(world[col]):
                    raise ValueError(f"Missing world observation: {name} {label}")
                date = quarter_end(label)
                series.setdefault(date, {"date": date})[key] = world[col]
    rows = sorted(series.values(), key=lambda r: r["date"])
    for row in rows:
        if not 0 < row["gold_usd_m"] < row["reserves_usd_m"]:
            raise ValueError("Gold/total reserve reconciliation failed")
    return {"source_file": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "source_url": "https://www.gold.org/goldhub/data/gold-reserves-by-country",
            "source_rows": "World row; quarter headers in row 2; USD millions",
            "as_of": rows[-1]["date"], "series": rows}


def treasury_rows(raw):
    lines = raw.decode("utf-8-sig").splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("country\tcountry_code\tdate\t"))
    result = {}
    for row in csv.DictReader(lines[start:], delimiter="\t"):
        if row.get("country_code") == "99990":
            value = float(row["for_treas_pos"])
            if not positive(value):
                raise ValueError("Invalid official Treasury holdings")
            result[row["date"]] = value
    if len(result) < 12:
        raise ValueError("Official Treasury history incomplete")
    return result


def btc_rows(payload):
    result = {}
    quantities = dict(payload["holdings"])
    for stamp, value in payload["holding_value_in_usd"]:
        quantity = quantities.get(stamp)
        if not positive(value) or not positive(quantity):
            raise ValueError("Invalid Bitcoin balance/value")
        date = datetime.fromtimestamp(stamp / 1000, timezone.utc).date().isoformat()
        result[date] = {"usd_m": value / 1e6, "btc": quantity}
    if len(result) < 8:
        raise ValueError("Insufficient Bitcoin history")
    return result


def treasury_history(raw):
    """MFH archive: USD billions; first duplicate month is the newer benchmark."""
    rows = list(csv.reader(io.StringIO(raw.decode('utf-8-sig')), delimiter='\t'))
    result = {}
    months = {name: i for i, name in enumerate(calendar.month_abbr) if name}
    dates = []
    for i, row in enumerate(rows):
        if row and row[0].strip() == 'Country':
            dates = []
            for month, year in zip(rows[i-1][1:], row[1:]):
                month, year = month.strip(), year.strip()
                dates.append(f'{year}-{months[month]:02d}' if month in months and year.isdigit() else None)
        elif row and row[0].strip() == 'For. Official':
            seen = set()
            for date, cell in zip(dates, row[1:]):
                if date is None or date in seen:
                    continue
                seen.add(date)
                value = float(cell.replace(',', '').strip()) * 1000
                if not positive(value):
                    raise ValueError('Invalid historical official Treasury holdings')
                if date in result:
                    raise ValueError(f'Duplicate archive year block: {date}')
                result[date] = value
    if '2000-03' not in result or len(result) < 240:
        raise ValueError('Treasury historical archive incomplete')
    return result


def build(gold, treasury, bitcoin):
    rows = []
    for source in gold["series"]:
        date = source["date"]
        if date[:7] not in treasury:
            continue
        denominator = source["reserves_usd_m"]
        row = {**source, "treasuries_usd_m": treasury[date[:7]],
               "gold_pct": 100 * source["gold_usd_m"] / denominator,
               "treasuries_pct": 100 * treasury[date[:7]] / denominator,
               "bitcoin_pct": None, "bitcoin_usd_m": None, "bitcoin_btc": None}
        # Exact quarter-end matches only. Never zero-fill or invent older BTC.
        if all(date in bitcoin[g] for g in GOVERNMENTS):
            row["bitcoin_usd_m"] = sum(bitcoin[g][date]["usd_m"] for g in GOVERNMENTS)
            row["bitcoin_btc"] = sum(bitcoin[g][date]["btc"] for g in GOVERNMENTS)
            row["bitcoin_pct"] = row["bitcoin_usd_m"] / denominator * 100
        rows.append(row)
    if len(rows) < 12 or sum(r["bitcoin_pct"] is not None for r in rows) < 2:
        raise ValueError("Not enough matched observations for three series")
    return {"schema_version": 1, "checked_at": datetime.now(timezone.utc).isoformat(),
            "as_of": rows[-1]["date"], "gold_source_file": gold["source_file"],
            "gold_sha256": gold["sha256"], "government_coverage": GOVERNMENTS,
            "series": rows, "sources": [
                {"label": "World Gold Council / IMF IFS", "url": gold["source_url"]},
                {"label": "U.S. Treasury TIC — foreign official, code 99990", "url": TIC},
                {"label": "Treasury MFH historical official holdings", "url": TIC_HISTORY},
                {"label": "CoinGecko — reported government holdings", "url": "https://www.coingecko.com/en/api/treasuries"}],
            "methodology": "Each value is divided by the same quarter-end WGC IMF World total reserves (including gold), in USD. Treasury official-sector coverage is broader than central banks. Bitcoin is a size comparison, not part of the official-reserve denominator. The three lines do not sum to 100%.",
            "bitcoin_note": "Incomplete, fixed four-government sample: United States, United Kingdom, El Salvador and Bhutan. CoinGecko-reported estimates may include seized assets and carried-forward balances. Not audited reserves, new purchases or a worldwide Bitcoin total. Free history starts in September 2025; earlier dates are missing, not zero.",
            "refresh_note": "Local snapshot. Gold requires a newer WGC quarterly workbook. Treasury and Bitcoin can be rechecked by the refresh script. No always-on cloud schedule is active."}


def save_atomic(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2) + "\n")
    tmp.replace(path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--gold-workbook", type=Path)
    args = parser.parse_args()
    gold = import_gold(args.gold_workbook) if args.gold_workbook else json.loads(SEED.read_text())
    treasury = {**treasury_history(fetch(TIC_HISTORY)), **treasury_rows(fetch(TIC))}
    bitcoin = {}
    for gov in GOVERNMENTS:
        print(f"Checking reported holdings: {gov}", flush=True)
        url = f"{CG}/public_treasury/{gov}/bitcoin/holding_chart?days=365&include_empty_intervals=true"
        bitcoin[gov] = btc_rows(json.loads(fetch(url)))
    payload = build(gold, treasury, bitcoin)
    payload['treasury_history_note'] = ('Treasury history begins March 2000. Before December 2011, holdings were survey-based estimates advanced using monthly transactions; later figures use SLT holdings reports. Benchmark revisions can cause jumps that are not purchases or sales. For duplicate archive months the newer benchmark is used; current Table 3 takes precedence from 2020. No quarters are interpolated.')
    if OUTPUT.exists():
        previous = json.loads(OUTPUT.read_text())
        if payload["as_of"] < previous["as_of"]:
            raise ValueError("Refusing an older snapshot")
        # Preserve older verified BTC quarter-ends outside the rolling free window.
        old = {r["date"]: r for r in previous["series"]}
        if previous["government_coverage"] == GOVERNMENTS:
            for row in payload["series"]:
                prior = old.get(row["date"], {})
                if row["bitcoin_pct"] is None and prior.get("bitcoin_usd_m") is not None:
                    for key in ("bitcoin_usd_m", "bitcoin_btc"):
                        row[key] = prior[key]
                    row["bitcoin_pct"] = row["bitcoin_usd_m"] / row["reserves_usd_m"] * 100
    save_atomic(OUTPUT, payload)
    if args.gold_workbook:
        save_atomic(SEED, gold)
    print(f"Saved {len(payload['series'])} quarters through {payload['as_of']}")


if __name__ == "__main__":
    main()
