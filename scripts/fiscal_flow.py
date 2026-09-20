#!/usr/bin/env python3
"""Build the frozen U.S. fiscal-flow archive and refresh its current snapshot.

Amounts are retained as integer dollars. Legacy MTS PDF observations are published
in whole millions and are converted exactly to dollars; API observations retain cents.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import tempfile
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data" / "fiscal-flow"
ARCHIVE = BASE / "archive"
CURRENT = BASE / "current.json"
DEBT = BASE / "debt.json"
MANIFEST = BASE / "manifest.json"
CLIENT = ROOT / "public" / "data" / "fiscal-flow.json"
CLIENT_MANIFEST = ROOT / "public" / "data" / "fiscal-flow-manifest.json"
API = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/mts/mts_table_9"
DEBT_API = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v2/accounting/od/debt_to_penny"
DEBT_SOURCE = "https://fiscaldata.treasury.gov/datasets/debt-to-the-penny/"
PDF = "https://fiscaldata.treasury.gov/static-data/published-reports/mts/MonthlyTreasuryStatement_{year}09.pdf"
RECEIPT_CODES = [20, 30, 50, 60, 70, 80, 90, 100, 110]
OUTLAY_CODES = [140, 150, 160, 170, 180, 190, 200, 210, 220, 230, 240, 250, 260, 270, 280, 290, 300, 320, 330]
TOTAL_RECEIPTS = 120
TOTAL_OUTLAYS = 340
USER_AGENT = "multi-asset-cycle-dashboard fiscal-flow/1.0"

PDF_LABELS = {
    20: "Individual income taxes", 30: "Corporation income taxes",
    50: "Employment and general retirement", 60: "Unemployment insurance",
    70: "Other retirement", 80: "Excise taxes", 90: "Estate and gift taxes",
    100: "Customs duties", 110: "Miscellaneous receipts",
    140: "National defense", 150: "International affairs",
    160: "General science, space, and technology", 170: "Energy",
    180: "Natural resources and environment", 190: "Agriculture",
    200: "Commerce and housing credit", 210: "Transportation",
    220: "Community and regional development",
    230: "Education, training, employment and social services", 240: "Health",
    250: "Medicare", 260: "Income security", 270: "Social security",
    280: "Veterans benefits and services", 290: "Administration of justice",
    300: "General government", 320: "Net interest",
    330: "Undistributed offsetting receipts",
}


def canonical_json(payload: Any) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def fetch_bytes(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=90) as response:
            if response.status != 200:
                raise RuntimeError(f"HTTP {response.status}: {url}")
            return response.read()
    except OSError as urllib_error:
        try:
            result = subprocess.run(
                ["curl", "--fail", "--silent", "--show-error", "--max-time", "90", "--user-agent", USER_AGENT, url],
                check=True,
                capture_output=True,
            )
        except (FileNotFoundError, subprocess.CalledProcessError) as curl_error:
            raise RuntimeError(f"Unable to fetch {url} with verified TLS") from curl_error
        if not result.stdout:
            raise RuntimeError(f"Empty response from {url}") from urllib_error
        return result.stdout


def api_rows(filters: str | None = None, sort: str = "line_code_nbr", page_size: int = 100) -> list[dict[str, str]]:
    fields = ["record_date", "record_fiscal_year", "classification_desc",
              "current_fytd_rcpt_outly_amt", "prior_fytd_rcpt_outly_amt",
              "line_code_nbr", "data_type_cd", "sequence_level_nbr", "print_order_nbr"]
    params = {"fields": ",".join(fields), "sort": sort, "page[size]": page_size}
    if filters:
        params["filter"] = filters
    query = urllib.parse.urlencode(params)
    payload = json.loads(fetch_bytes(f"{API}?{query}"))
    return payload["data"]


def debt_rows(start_date: str = "2006-09-01") -> list[dict[str, str]]:
    params = {
        "fields": "record_date,tot_pub_debt_out_amt",
        "filter": f"record_date:gte:{start_date}",
        "sort": "record_date",
        "page[size]": 10000,
    }
    payload = json.loads(fetch_bytes(f"{DEBT_API}?{urllib.parse.urlencode(params)}"))
    rows = payload["data"]
    total = int(payload.get("meta", {}).get("total-count", len(rows)))
    if len(rows) != total:
        raise RuntimeError(f"Debt to the Penny response was incomplete: {len(rows)} of {total} rows")
    return rows


def build_debt_context(snapshots: list[dict[str, Any]], rows: list[dict[str, str]]) -> dict[str, Any]:
    observations = [
        {
            "record_date": row["record_date"],
            "total_public_debt_outstanding_dollars": dollars(row["tot_pub_debt_out_amt"]),
        }
        for row in rows
    ]
    if not observations:
        raise RuntimeError("No Debt to the Penny observations available")

    def latest_on_or_before(date: str) -> dict[str, Any]:
        eligible = [row for row in observations if row["record_date"] <= date]
        if not eligible:
            raise RuntimeError(f"No debt observation on or before {date}")
        return eligible[-1]

    by_fiscal_year = {
        str(snapshot["fiscal_year"]): latest_on_or_before(snapshot["period_end"])
        for snapshot in snapshots
    }
    return {
        "definition": "Total Public Debt Outstanding: debt held by the public plus intragovernmental holdings.",
        "source_url": DEBT_SOURCE,
        "by_fiscal_year": by_fiscal_year,
        "current": observations[-1],
    }


def dollars(value: str) -> int:
    return int(Decimal(value).quantize(Decimal("1")))


def _flow_item(row: dict[str, str], amount_field: str) -> dict[str, Any]:
    return {"line_code": int(row["line_code_nbr"]), "label": row["classification_desc"], "amount_dollars": dollars(row[amount_field])}


def snapshot_from_api(rows: list[dict[str, str]], fiscal_year: int, amount_field: str = "current_fytd_rcpt_outly_amt", *, status: str, period_end: str | None = None) -> dict[str, Any]:
    by_code = {int(row["line_code_nbr"]): row for row in rows}
    missing = set(RECEIPT_CODES + OUTLAY_CODES + [TOTAL_RECEIPTS, TOTAL_OUTLAYS]) - set(by_code)
    if missing:
        raise ValueError(f"FY{fiscal_year} missing Table 9 line codes: {sorted(missing)}")
    receipts = [_flow_item(by_code[code], amount_field) for code in RECEIPT_CODES]
    outlay_rows = [_flow_item(by_code[code], amount_field) for code in OUTLAY_CODES]
    positive = [item for item in outlay_rows if item["amount_dollars"] >= 0]
    offsets = [item for item in outlay_rows if item["amount_dollars"] < 0]
    total_receipts = dollars(by_code[TOTAL_RECEIPTS][amount_field])
    total_outlays = dollars(by_code[TOTAL_OUTLAYS][amount_field])
    return finish_snapshot({
        "fiscal_year": fiscal_year, "label": f"FY{fiscal_year}", "status": status,
        "period_end": period_end or rows[0]["record_date"],
        "precision": "cents rounded to nearest dollar", "source_type": "FiscalData API Table 9",
        "source_url": API, "receipts": receipts, "positive_outlays": positive,
        "offsetting_outlays": offsets, "total_receipts_dollars": total_receipts,
        "net_outlays_dollars": total_outlays,
    })


def finish_snapshot(s: dict[str, Any]) -> dict[str, Any]:
    receipt_sum = sum(x["amount_dollars"] for x in s["receipts"])
    outlay_sum = sum(x["amount_dollars"] for x in s["positive_outlays"] + s["offsetting_outlays"])
    s["deficit_dollars"] = s["net_outlays_dollars"] - s["total_receipts_dollars"]
    s["net_interest_dollars"] = next(x["amount_dollars"] for x in s["positive_outlays"] + s["offsetting_outlays"] if x["line_code"] == 320)
    s["reconciliation"] = {
        "receipt_detail_less_total_dollars": receipt_sum - s["total_receipts_dollars"],
        "outlay_detail_less_total_dollars": outlay_sum - s["net_outlays_dollars"],
        "identity_difference_dollars": s["total_receipts_dollars"] + s["deficit_dollars"] - s["net_outlays_dollars"],
    }
    return s


def _parse_pdf_number(raw: str) -> int:
    raw = raw.replace("−", "-").replace("–", "-").replace("—", "-").replace(",", "").replace(" ", "").strip()
    raw = re.sub(r"^[+ ]+", "", raw)
    return int(raw) * 1_000_000


def snapshot_from_pdf(content: bytes, fiscal_year: int) -> dict[str, Any]:
    with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp:
        tmp.write(content); tmp.flush()
        text = "\n".join(page.extract_text() or "" for page in PdfReader(tmp.name).pages)
    marker = re.search(r"Table 9\.\s+Summary of Receipts by Source, and Outlays by Function", text, re.I)
    if not marker:
        raise ValueError(f"FY{fiscal_year} Table 9 not found")
    table = text[marker.start():]
    end = re.search(r"\nTable 10\.", table, re.I)
    if end:
        table = table[:end.start()]
    # PDF text layers occasionally insert spaces next to thousands separators.
    table = re.sub(r"(?<=\d)\s*,\s*(?=\d)", ",", table)
    table = re.sub(r"(?<=\d),(\d)\s+(\d{2}\b)", r",\1\2", table)
    table = re.sub(r"(?<=\d),(\d{2})\s+(\d\b)", r",\1\2", table)
    table = re.sub(r"\b(\d)\s+(\d,\d{3})\b", r"\1\2", table)
    items: dict[int, dict[str, Any]] = {}
    number = r"[+−\-]?\s*\d[\d,]*"
    for code, label in PDF_LABELS.items():
        # MTS extraction can place a footnote digit before the first amount.
        pattern = re.escape(label) + r"[^\n]*?\s+(?:\d\s+)?(" + number + r")\s+(" + number + r")\s+(" + number + r")"
        match = re.search(pattern, table, re.I)
        if not match:
            raise ValueError(f"FY{fiscal_year} missing PDF row: {label}")
        items[code] = {"line_code": code, "label": label, "amount_dollars": _parse_pdf_number(match.group(2))}
    total_matches = list(re.finditer(r"\n\s*Total\b[^\n]*?\s+(" + number + r")\s+(" + number + r")\s+(" + number + r")", table, re.I))
    if len(total_matches) < 2:
        raise ValueError(f"FY{fiscal_year} receipt/outlay totals not found")
    total_receipts = _parse_pdf_number(total_matches[0].group(2))
    total_outlays = _parse_pdf_number(total_matches[1].group(2))
    ordered = [items[c] for c in OUTLAY_CODES]
    return finish_snapshot({
        "fiscal_year": fiscal_year, "label": f"FY{fiscal_year}", "status": "final-frozen",
        "period_end": f"{fiscal_year}-09-30", "precision": "whole USD millions converted to dollars",
        "source_type": "Monthly Treasury Statement September PDF, Table 9",
        "source_url": PDF.format(year=fiscal_year),
        "source_sha256": sha256_bytes(content), "receipts": [items[c] for c in RECEIPT_CODES],
        "positive_outlays": [x for x in ordered if x["amount_dollars"] >= 0],
        "offsetting_outlays": [x for x in ordered if x["amount_dollars"] < 0],
        "total_receipts_dollars": total_receipts, "net_outlays_dollars": total_outlays,
    })


def fetch_archive_year(year: int) -> dict[str, Any]:
    if year <= 2014:
        return snapshot_from_pdf(fetch_bytes(PDF.format(year=year)), year)
    rows = api_rows(f"record_date:eq:{year}-09-30")
    return snapshot_from_api(rows, year, status="final-frozen", period_end=f"{year}-09-30")


def latest_current() -> dict[str, Any]:
    discovery = api_rows(sort="-record_date", page_size=1)
    if not discovery:
        raise RuntimeError("No current Table 9 rows available")
    date = discovery[0]["record_date"]
    fiscal_year = int(discovery[0]["record_fiscal_year"])
    rows = api_rows(f"record_date:eq:{date}")
    current = snapshot_from_api(rows, fiscal_year, status="current-ytd", period_end=date)
    prior_year = fiscal_year - 1
    prior = snapshot_from_api(rows, prior_year, amount_field="prior_fytd_rcpt_outly_amt", status="prior-year-same-period", period_end=date)
    current["label"] = "Current"
    current["prior_year_same_period"] = {
        "fiscal_year": prior_year, "period_through": date[5:],
        "total_receipts_dollars": prior["total_receipts_dollars"], "net_outlays_dollars": prior["net_outlays_dollars"],
        "deficit_dollars": prior["deficit_dollars"], "net_interest_dollars": prior["net_interest_dollars"],
        "receipt_change_dollars": current["total_receipts_dollars"] - prior["total_receipts_dollars"],
        "outlay_change_dollars": current["net_outlays_dollars"] - prior["net_outlays_dollars"],
        "deficit_change_dollars": current["deficit_dollars"] - prior["deficit_dollars"],
        "net_interest_change_dollars": current["net_interest_dollars"] - prior["net_interest_dollars"],
    }
    return current


def write_archive(snapshot: dict[str, Any], migrate: bool = False) -> Path:
    path = ARCHIVE / f"fy{snapshot['fiscal_year']}.json"
    content = canonical_json(snapshot)
    if path.exists() and not migrate:
        raise FileExistsError(f"Refusing to overwrite immutable archive: {path}; use --migrate-existing")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def rebuild_manifest_and_client() -> None:
    archive_rows = [json.loads(p.read_text()) for p in sorted(ARCHIVE.glob("fy*.json"))]
    current = json.loads(CURRENT.read_text())
    debt = json.loads(DEBT.read_text())
    entries = []
    for path in sorted(ARCHIVE.glob("fy*.json")):
        row = json.loads(path.read_text())
        entries.append({"fiscal_year": row["fiscal_year"], "status": row["status"], "source_url": row["source_url"], "precision": row["precision"], "file": str(path.relative_to(ROOT)), "sha256": sha256_bytes(path.read_bytes())})
    manifest = {"schema_version": 2, "archive_policy": "immutable", "archive": entries,
                "current": {"fiscal_year": current["fiscal_year"], "status": current["status"], "source_url": current["source_url"], "precision": current["precision"], "file": str(CURRENT.relative_to(ROOT)), "sha256": sha256_bytes(CURRENT.read_bytes())},
                "debt": {"source_url": debt["source_url"], "file": str(DEBT.relative_to(ROOT)), "sha256": sha256_bytes(DEBT.read_bytes())}}
    MANIFEST.write_bytes(canonical_json(manifest))
    CLIENT_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    CLIENT_MANIFEST.write_bytes(canonical_json(manifest))
    CLIENT.parent.mkdir(parents=True, exist_ok=True)
    CLIENT.write_bytes(canonical_json({"schema_version": 2, "generated_at": datetime.now(timezone.utc).isoformat(), "years": archive_rows, "current": current, "debt": debt, "manifest_url": "/public/data/fiscal-flow-manifest.json"}))


def run(args: argparse.Namespace) -> None:
    BASE.mkdir(parents=True, exist_ok=True)
    if args.backfill:
        for year in range(2006, 2026):
            path = ARCHIVE / f"fy{year}.json"
            if path.exists() and not args.migrate_existing:
                continue
            write_archive(fetch_archive_year(year), migrate=args.migrate_existing)
            print(f"archived FY{year}")
    current = latest_current()
    CURRENT.write_bytes(canonical_json(current))
    archive_rows = [json.loads(p.read_text()) for p in sorted(ARCHIVE.glob("fy*.json"))]
    DEBT.write_bytes(canonical_json(build_debt_context(archive_rows, debt_rows())))
    rebuild_manifest_and_client()
    print(json.dumps({"archive_years": len(list(ARCHIVE.glob('fy*.json'))), "current_through": current["period_end"], "client": str(CLIENT)}, indent=2))


def promote(year: int) -> None:
    current = json.loads(CURRENT.read_text())
    if current["fiscal_year"] != year or current["period_end"] != f"{year}-09-30":
        raise RuntimeError(f"Promotion requires reconciled September close for FY{year}; current is {current['period_end']}")
    promoted = {k: v for k, v in current.items() if k != "prior_year_same_period"}
    promoted.update({"label": f"FY{year}", "status": "final-frozen"})
    write_archive(promoted)
    archive_rows = [json.loads(p.read_text()) for p in sorted(ARCHIVE.glob("fy*.json"))]
    DEBT.write_bytes(canonical_json(build_debt_context(archive_rows, debt_rows())))
    rebuild_manifest_and_client()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backfill", action="store_true", help="create missing FY2006-FY2025 archives")
    parser.add_argument("--migrate-existing", action="store_true", help="explicitly replace archives during a reviewed migration")
    parser.add_argument("--promote", type=int, metavar="FY", help="freeze a reconciled September current snapshot")
    args = parser.parse_args()
    if args.promote:
        promote(args.promote)
    else:
        run(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
