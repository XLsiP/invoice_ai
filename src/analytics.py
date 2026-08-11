"""Shared invoice analytics.

This is the single source of truth for every vendor, product, and spending
calculation in the app. Both the Insights page and the Executive Report
read from these functions so the two surfaces can never disagree with
each other, and so a fix or change only has to happen in one place.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional


def safe_float(value: Any) -> float:
    """Safely convert any value into a float."""

    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def normalize_text(value: Any) -> str:
    """Normalize text for case-insensitive comparisons."""

    if value is None:
        return ""

    return str(value).strip().lower()


def parse_invoice_date(value: Optional[str]):
    """Try parsing an invoice date in any of the formats we accept."""

    if not value:
        return None

    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            pass

    return None


# ---------------------------------------------------------------------
# Portfolio-level metrics
# ---------------------------------------------------------------------


def total_spending(invoices: List[Dict[str, Any]]) -> float:
    """Return total spending across every invoice."""

    return round(
        sum(safe_float(invoice.get("total_due")) for invoice in invoices),
        2,
    )


def average_invoice(invoices: List[Dict[str, Any]]) -> float:
    """Average invoice amount."""

    if not invoices:
        return 0.0

    return round(total_spending(invoices) / len(invoices), 2)


def largest_invoice(invoices: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Return the single largest invoice."""

    if not invoices:
        return {}

    return max(invoices, key=lambda invoice: safe_float(invoice.get("total_due")))


def validation_summary(invoices: List[Dict[str, Any]]) -> Dict[str, int]:
    """Count how many invoices are valid vs. need review."""

    valid = sum(1 for invoice in invoices if invoice.get("validation_status") == "Valid")

    return {"valid": valid, "needs_review": len(invoices) - valid}


def vendor_count(invoices: List[Dict[str, Any]]) -> int:
    """Count distinct vendors."""

    return len(
        {
            normalize_text(invoice.get("vendor"))
            for invoice in invoices
            if normalize_text(invoice.get("vendor"))
        }
    )


def line_item_count(invoices: List[Dict[str, Any]]) -> int:
    """Count purchased line items across every invoice."""

    return sum(len(invoice.get("line_items") or []) for invoice in invoices)


def overall_summary(invoices: List[Dict[str, Any]]) -> Dict[str, Any]:
    """High-level portfolio snapshot, used by both Insights and the AI assistant."""

    validation = validation_summary(invoices)

    return {
        "invoice_count": len(invoices),
        "vendor_count": vendor_count(invoices),
        "line_item_count": line_item_count(invoices),
        "total_spend": total_spending(invoices),
        "average_invoice": average_invoice(invoices),
        "valid_count": validation["valid"],
        "needs_review_count": validation["needs_review"],
    }


# ---------------------------------------------------------------------
# Vendor-level metrics
# ---------------------------------------------------------------------


def vendor_summary(
    invoices: List[Dict[str, Any]],
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Per-vendor totals, sorted by spend descending."""

    vendors: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {"vendor": "", "total_spend": 0.0, "invoice_count": 0, "_totals": []}
    )

    for invoice in invoices:
        vendor = invoice.get("vendor") or "Unknown Vendor"
        row = vendors[vendor]
        row["vendor"] = vendor
        row["invoice_count"] += 1

        due = safe_float(invoice.get("total_due"))
        row["total_spend"] += due
        row["_totals"].append(due)

    rows = []

    for row in vendors.values():
        totals = row.pop("_totals")
        row["total_spend"] = round(row["total_spend"], 2)
        row["average_invoice"] = (
            round(row["total_spend"] / row["invoice_count"], 2)
            if row["invoice_count"]
            else 0.0
        )
        row["largest_invoice"] = round(max(totals), 2) if totals else 0.0
        rows.append(row)

    rows.sort(key=lambda row: row["total_spend"], reverse=True)

    return rows[:limit] if limit else rows


def vendor_lookup(
    invoices: List[Dict[str, Any]],
    vendor_query: str,
) -> Optional[Dict[str, Any]]:
    """Return invoice and item details for the closest vendor name match."""

    query = normalize_text(vendor_query)

    if not query:
        return None

    matches = [
        invoice for invoice in invoices if query in normalize_text(invoice.get("vendor"))
    ]

    if not matches:
        return None

    vendor_name = matches[0].get("vendor") or vendor_query
    top_items = purchased_item_summary(matches, limit=5)

    return {
        "vendor": vendor_name,
        "invoice_count": len(matches),
        "total_spend": total_spending(matches),
        "average_invoice": average_invoice(matches),
        "largest_invoice": safe_float(largest_invoice(matches).get("total_due")),
        "top_items": [
            {"description": row["description"], "total_spend": row["spend"]}
            for row in top_items
        ],
        "invoices": matches,
    }


def vendor_growth(invoices: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Compare vendor spending month-to-month."""

    vendor_months: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))

    for invoice in invoices:
        vendor = invoice.get("vendor") or "Unknown"
        date = parse_invoice_date(invoice.get("invoice_date"))

        if not date:
            continue

        vendor_months[vendor][date.strftime("%Y-%m")] += safe_float(
            invoice.get("total_due")
        )

    report = []

    for vendor, history in vendor_months.items():
        ordered = sorted(history.items())

        if len(ordered) < 2:
            continue

        previous, current = ordered[-2][1], ordered[-1][1]
        change = current - previous
        percent = (change / previous) * 100 if previous > 0 else 0

        report.append(
            {
                "vendor": vendor,
                "previous_month": round(previous, 2),
                "current_month": round(current, 2),
                "change": round(change, 2),
                "percent_change": round(percent, 2),
            }
        )

    report.sort(key=lambda row: abs(row["percent_change"]), reverse=True)

    return report


def duplicate_vendor_check(invoices: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Look for duplicate vendor + invoice number combinations."""

    seen: Dict[Any, Dict[str, Any]] = {}
    duplicates = []

    for invoice in invoices:
        key = (
            (invoice.get("vendor") or "").lower(),
            (invoice.get("invoice_number") or "").lower(),
        )

        if key in seen:
            duplicates.append(invoice)
        else:
            seen[key] = invoice

    return duplicates


# ---------------------------------------------------------------------
# Product / line-item metrics
# ---------------------------------------------------------------------


def purchased_item_summary(
    invoices: List[Dict[str, Any]],
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Per-item totals across every invoice, sorted by spend descending."""

    items: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {
            "description": "",
            "quantity": 0.0,
            "spend": 0.0,
            "invoice_count": 0,
            "_vendors": set(),
            "_unit_prices": [],
        }
    )

    for invoice in invoices:
        vendor = invoice.get("vendor") or "Unknown vendor"

        for item in invoice.get("line_items", []) or []:
            description = str(item.get("description") or "").strip()

            if not description:
                continue

            row = items[description]
            row["description"] = description
            row["quantity"] += safe_float(item.get("quantity"))
            row["spend"] += safe_float(item.get("line_total"))
            row["invoice_count"] += 1
            row["_vendors"].add(vendor)
            row["_unit_prices"].append(safe_float(item.get("unit_price")))

    rows = []

    for row in items.values():
        vendors = row.pop("_vendors")
        unit_prices = row.pop("_unit_prices")
        row["quantity"] = round(row["quantity"], 2)
        row["spend"] = round(row["spend"], 2)
        row["vendor_count"] = len(vendors)
        row["average_unit_price"] = (
            round(sum(unit_prices) / len(unit_prices), 2) if unit_prices else 0.0
        )
        rows.append(row)

    rows.sort(key=lambda row: row["spend"], reverse=True)

    return rows[:limit] if limit else rows


def search_items(
    invoices: List[Dict[str, Any]],
    search_term: str,
) -> List[Dict[str, Any]]:
    """Find invoice line items matching a search term."""

    term = normalize_text(search_term)

    if not term:
        return []

    results = []

    for invoice in invoices:
        for item in invoice.get("line_items", []) or []:
            description = str(item.get("description") or "").strip()

            if term not in normalize_text(description):
                continue

            results.append(
                {
                    "invoice_id": invoice.get("id"),
                    "vendor": invoice.get("vendor"),
                    "invoice_number": invoice.get("invoice_number"),
                    "invoice_date": invoice.get("invoice_date"),
                    "source_file": invoice.get("source_file"),
                    "description": description,
                    "quantity": safe_float(item.get("quantity")),
                    "unit_price": safe_float(item.get("unit_price")),
                    "line_total": safe_float(item.get("line_total")),
                }
            )

    results.sort(
        key=lambda row: (row.get("invoice_date") or "", row.get("invoice_id") or 0),
        reverse=True,
    )

    return results


# ---------------------------------------------------------------------
# Time-based metrics
# ---------------------------------------------------------------------


def monthly_spending(invoices: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Spending grouped by month."""

    months: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {"month": "", "invoice_count": 0, "total_spend": 0.0}
    )

    for invoice in invoices:
        date = parse_invoice_date(invoice.get("invoice_date"))

        if not date:
            continue

        key = date.strftime("%Y-%m")
        months[key]["month"] = key
        months[key]["invoice_count"] += 1
        months[key]["total_spend"] += safe_float(invoice.get("total_due"))

    rows = list(months.values())

    for row in rows:
        row["total_spend"] = round(row["total_spend"], 2)

    rows.sort(key=lambda row: row["month"])

    return rows


def current_month_summary(invoices: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Spending metrics for the current calendar month."""

    now = datetime.now()
    prefix = now.strftime("%Y-%m")

    matches = [
        invoice
        for invoice in invoices
        if str(invoice.get("invoice_date") or "").startswith(prefix)
    ]

    return {
        "month": now.strftime("%B %Y"),
        "invoice_count": len(matches),
        "total_spend": total_spending(matches),
        "average_invoice": average_invoice(matches) if matches else 0.0,
        "invoices": matches,
    }


def review_queue(invoices: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Invoices that still need manual review."""

    return [invoice for invoice in invoices if invoice.get("validation_status") != "Valid"]