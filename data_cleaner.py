"""
data_cleaner.py
Deterministic cleaning for Work Orders and Deals data.
Handles every known data quality issue found in the uploaded Excel files.
"""

import re
import json
import math
from pathlib import Path
from datetime import datetime
from typing import Any

# ─── Helpers ──────────────────────────────────────────────────────────────────

MISSING_SENTINELS = {
    "", "nan", "none", "n/a", "na", "null", "-", "--", "not available",
    "not applicable", "tbd", "tbc", "unknown"
}


def is_missing(val: Any) -> bool:
    if val is None:
        return True
    if isinstance(val, float) and math.isnan(val):
        return True
    if isinstance(val, str) and val.strip().lower() in MISSING_SENTINELS:
        return True
    return False


def clean_str(val: Any) -> str | None:
    """Strip whitespace and surrounding quotes. Return None if missing."""
    if is_missing(val):
        return None
    s = str(val).strip()
    # Remove surrounding single or double quotes  e.g. "'Completed'" → "Completed"
    if (s.startswith("'") and s.endswith("'")) or \
       (s.startswith('"') and s.endswith('"')):
        s = s[1:-1].strip()
    return s if s and s.lower() not in MISSING_SENTINELS else None


def clean_currency(val: Any) -> float | None:
    """Parse currency: strip ₹, $, commas, spaces. Return float or None."""
    if is_missing(val):
        return None
    s = str(val).strip()
    s = re.sub(r"[₹$,\s]", "", s)
    try:
        return float(s)
    except ValueError:
        return None

def normalize_keys(row: dict) -> dict:
    return {
        k.strip().lower(): v
        for k, v in row.items()
    }

def clean_date(val: Any) -> str | None:
    """Normalize date to ISO YYYY-MM-DD string or None."""
    if is_missing(val):
        return None
    if isinstance(val, datetime):
        return val.strftime("%Y-%m-%d")
    s = str(val).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y",
                "%m/%d/%Y", "%d %b %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(s.split(" ")[0], fmt.split(" ")[0]).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return s  # return as-is if unparseable, so we don't silently lose data


def clean_quantity(val: Any) -> dict:
    """
    Handle mixed quantity fields like '5360 HA', '3956HA', '2 location', '45days'.
    Returns { "raw": str, "numeric": float|None, "unit": str|None }
    """
    if is_missing(val):
        return {"raw": None, "numeric": None, "unit": None}

    raw = str(val).strip()
    # Replace commas in numbers like '1,310.850'
    cleaned = raw.replace(",", "")
    match = re.match(r"^([\d.]+)\s*([A-Za-z].*)?$", cleaned)
    if match:
        try:
            numeric = float(match.group(1))
            unit = match.group(2).strip() if match.group(2) else None
            return {"raw": raw, "numeric": numeric, "unit": unit}
        except ValueError:
            pass
    return {"raw": raw, "numeric": None, "unit": None}


def normalize_sector(val: Any) -> str | None:
    """Canonical sector names, case-insensitive."""
    s = clean_str(val)
    if s is None:
        return None
    mapping = {
        "mining": "Mining",
        "powerline": "Powerline",
        "renewables": "Renewables",
        "renewable": "Renewables",
        "railways": "Railways",
        "railway": "Railways",
        "construction": "Construction",
        "dsp": "DSP",
        "tender": "Tender",
        "aviation": "Aviation",
        "manufacturing": "Manufacturing",
        "security and surveillance": "Security & Surveillance",
        "security & surveillance": "Security & Surveillance",
        "others": "Others",
        "other": "Others",
    }
    return mapping.get(s.lower(), s)


def normalize_execution_status(val: Any) -> str | None:
    s = clean_str(val)
    if s is None:
        return None
    mapping = {
        "completed": "Completed",
        "not started": "Not Started",
        "ongoing": "Ongoing",
        "executed until current month": "Ongoing",
        "pause / struck": "On Hold",
        "pause/struck": "On Hold",
        "partial completed": "Partially Completed",
        "partially completed": "Partially Completed",
        "details pending from client": "Pending Client",
    }
    return mapping.get(s.lower(), s)


def normalize_deal_stage(val: Any) -> str | None:
    s = clean_str(val)
    if s is None:
        return None
    # Drop header-row contamination
    if s.lower() in ("deal stage", "sector/service", "closure probability"):
        return None
    return s


def normalize_deal_status(val: Any) -> str | None:
    s = clean_str(val)
    if s is None:
        return None
    if s.lower() in ("deal status",):
        return None
    return s


def normalize_probability(val: Any) -> str | None:
    s = clean_str(val)
    if s is None:
        return None
    if s.lower() in ("closure probability",):
        return None
    return s.capitalize()


def normalize_billing_status(val: Any) -> str | None:
    s = clean_str(val)
    if s is None:
        return None
    # Fix casing: 'BIlled' → 'Billed'
    if s.lower() == "billed":
        return "Billed"
    return s


# ─── Work Orders Cleaner ──────────────────────────────────────────────────────

def clean_work_order(row: dict) -> dict:
    return {
        "deal_name":             clean_str(row.get("Deal name masked")),
        "customer_code":         clean_str(row.get("Customer Name Code")),
        "serial":                clean_str(row.get("Serial #")),
        "nature_of_work":        clean_str(row.get("Nature of Work")),
        "last_recurring_month":  clean_str(row.get("Last executed month of recurring project")),
        "execution_status":      normalize_execution_status(row.get("Execution Status")),
        "data_delivery_date":    clean_date(row.get("Data Delivery Date")),
        "po_loi_date":           clean_date(row.get("Date of PO/LOI")),
        "document_type":         clean_str(row.get("Document Type")),
        "probable_start":        clean_date(row.get("Probable Start Date")),
        "probable_end":          clean_date(row.get("Probable End Date")),
        "bd_personnel":          clean_str(row.get("BD/KAM Personnel code")),
        "sector":                normalize_sector(row.get("Sector")),
        "type_of_work":          clean_str(row.get("Type of Work")),
        "has_software_platform": clean_str(row.get("Is any Skylark software platform part of the client deliverables in this deal?")),
        "last_invoice_date":     clean_date(row.get("Last invoice date")),
        "latest_invoice_no":     clean_str(row.get("latest invoice no.")),
        # Currency fields
        "amount_excl_gst":       clean_currency(row.get("Amount in Rupees (Excl of GST) (Masked)")),
        "amount_incl_gst":       clean_currency(row.get("Amount in Rupees (Incl of GST) (Masked)")),
        "billed_excl_gst":       clean_currency(row.get("Billed Value in Rupees (Excl of GST.) (Masked)")),
        "billed_incl_gst":       clean_currency(row.get("Billed Value in Rupees (Incl of GST.) (Masked)")),
        "collected_incl_gst":    clean_currency(row.get("Collected Amount in Rupees (Incl of GST.) (Masked)")),
        "to_be_billed_excl_gst": clean_currency(row.get("Amount to be billed in Rs. (Exl. of GST)")),
        "to_be_billed_incl_gst": clean_currency(row.get("Amount to be billed in Rs. (Incl. of GST)")),
        "amount_receivable":     clean_currency(row.get("Amount Receivable (Masked)")),
        # Quantity (mixed units)
        "qty_by_ops":            clean_quantity(row.get("Quantity by Ops")),
        "qty_as_per_po":         clean_quantity(row.get("Quantities as per PO")),
        "qty_billed":            clean_quantity(row.get("Quantity billed (till date)")),
        "qty_balance":           clean_quantity(row.get("Balance in quantity")),
        # Status fields
        "invoice_status":        clean_str(row.get("Invoice Status")),
        "wo_status":             clean_str(row.get("WO Status (billed)")),
        "billing_status":        normalize_billing_status(row.get("Billing Status")),
        "collection_status":     clean_str(row.get("Collection status")),
        "collection_date":       clean_date(row.get("Collection Date")),
        "ar_priority":           clean_str(row.get("AR Priority account")),
        "expected_billing_month": clean_str(row.get("Expected Billing Month")),
        "actual_billing_month":  clean_str(row.get("Actual Billing Month")),
        "actual_collection_month": clean_str(row.get("Actual Collection Month")),
    }


# ─── Deals Cleaner ───────────────────────────────────────────────────────────

def clean_deal(row: dict) -> dict:
    # Skip rows that are header-row duplicates embedded in data
    deal_name = clean_str(row.get("Deal Name"))
    if deal_name and deal_name.lower() in ("deal name", "deal stage"):
        return None

    stage = normalize_deal_stage(row.get("Deal Stage"))
    status = normalize_deal_status(row.get("Deal Status"))

    # Skip if both name and stage are null (completely empty row)
    if deal_name is None and stage is None:
        return None

    return {
        "deal_name":          deal_name,
        "owner_code":         clean_str(row.get("Owner code")),
        "client_code":        clean_str(row.get("Client Code")),
        "deal_status":        status,
        "close_date_actual":  clean_date(row.get("Close Date (A)")),
        "closure_probability": normalize_probability(row.get("Closure Probability")),
        "deal_value":         clean_currency(row.get("Masked Deal value")),
        "tentative_close_date": clean_date(row.get("Tentative Close Date")),
        "deal_stage":         stage,
        "product_deal":       clean_str(row.get("Product deal")),
        "sector":             normalize_sector(row.get("Sector/service")),
        "created_date":       clean_date(row.get("Created Date")),
    }


# ─── Main entry ──────────────────────────────────────────────────────────────

def clean_and_enrich(raw_wo: list, raw_deals: list) -> tuple[list, list, dict]:
    """
    Clean both datasets. Returns (clean_wo, clean_deals, quality_report).
    """
    # ── Clean Work Orders ──
    clean_wo = []
    wo_issues = {"quoted_strings_fixed": 0, "missing_filled_none": 0,
                 "currency_parsed": 0, "qty_split": 0, "status_normalized": 0}

    for row in raw_wo:
        cleaned = clean_work_order(row)
        if cleaned["execution_status"] != row.get("Execution Status"):
            wo_issues["status_normalized"] += 1
        if cleaned["amount_excl_gst"] is not None:
            wo_issues["currency_parsed"] += 1
        if cleaned.get("qty_as_per_po", {}).get("unit"):
            wo_issues["qty_split"] += 1
        clean_wo.append(cleaned)

    # ── Clean Deals ──
    clean_deals = []
    deal_issues = {"header_rows_removed": 0, "status_normalized": 0,
                   "sector_normalized": 0, "currency_parsed": 0}

    for row in raw_deals:
        cleaned = clean_deal(row)
        if cleaned is None:
            deal_issues["header_rows_removed"] += 1
            continue
        if cleaned["sector"]:
            deal_issues["sector_normalized"] += 1
        if cleaned["deal_value"] is not None:
            deal_issues["currency_parsed"] += 1
        clean_deals.append(cleaned)

    # ── Quality report ──
    wo_nulls = {k: sum(1 for r in clean_wo if r.get(k) is None)
                for k in clean_wo[0]} if clean_wo else {}
    deal_nulls = {k: sum(1 for r in clean_deals if r.get(k) is None)
                  for k in clean_deals[0]} if clean_deals else {}

    report = {
        "work_orders": {
            "total_records": len(clean_wo),
            "fixes_applied": wo_issues,
            "null_counts": {k: v for k, v in wo_nulls.items() if v > 0}
        },
        "deals": {
            "total_records": len(clean_deals),
            "fixes_applied": deal_issues,
            "null_counts": {k: v for k, v in deal_nulls.items() if v > 0}
        }
    }

    return clean_wo, clean_deals, report


# ─── Pre-process and save cleaned JSON files ─────────────────────────────────

# def rebuild_cleaned_files(base_path: Path):
#     """Load raw JSONs, clean them, write cleaned versions."""
#     raw_wo    = json.loads((base_path / "wo_data.json").read_text())
#     raw_deals = json.loads((base_path / "deals_data.json").read_text())

#     clean_wo, clean_deals, report = clean_and_enrich(raw_wo, raw_deals)

#     (base_path / "wo_clean.json").write_text(json.dumps(clean_wo, default=str, indent=2))
#     (base_path / "deals_clean.json").write_text(json.dumps(clean_deals, default=str, indent=2))
#     (base_path / "quality_report.json").write_text(json.dumps(report, default=str, indent=2))

#     return clean_wo, clean_deals, report


# if __name__ == "__main__":
#     base = Path(__file__).parent
#     _, _, report = rebuild_cleaned_files(base)
#     print(json.dumps(report, indent=2))
