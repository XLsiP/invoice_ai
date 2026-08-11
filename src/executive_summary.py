from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from src.database import (
    get_all_invoices,
)
from dotenv import load_dotenv

load_dotenv()


def safe_float(value: Any) -> float:
    """Safely convert any value to float."""

    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def safe_int(value: Any) -> int:
    """Safely convert any value to int."""

    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def parse_invoice_date(value: str):
    """Try parsing invoice dates."""

    if not value:
        return None

    formats = [
        "%Y-%m-%d",
        "%m/%d/%Y",
        "%m-%d-%Y",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            pass

    return None


def load_invoice_data(
    database_path: Path,
) -> List[Dict[str, Any]]:
    """
    Load every invoice.

    This is the single source of truth used
    throughout executive reporting.
    """

    return get_all_invoices(database_path)


def total_spending(
    invoices: List[Dict[str, Any]],
) -> float:
    """Return total spending."""

    return round(
        sum(
            safe_float(
                invoice.get("total_due")
            )
            for invoice in invoices
        ),
        2,
    )


def average_invoice(
    invoices: List[Dict[str, Any]],
) -> float:
    """Average invoice amount."""

    if not invoices:
        return 0.0

    return round(
        total_spending(invoices)
        / len(invoices),
        2,
    )


def largest_invoice(
    invoices: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Return largest invoice."""

    if not invoices:
        return {}

    return max(
        invoices,
        key=lambda invoice:
        safe_float(
            invoice.get("total_due")
        ),
    )


def validation_summary(
    invoices: List[Dict[str, Any]],
) -> Dict[str, int]:

    valid = 0
    review = 0

    for invoice in invoices:

        if (
            invoice.get(
                "validation_status"
            )
            == "Valid"
        ):
            valid += 1

        else:
            review += 1

    return {
        "valid": valid,
        "needs_review": review,
    }


def vendor_summary(
    invoices: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Total spending by vendor.
    """

    vendors = defaultdict(
        lambda: {
            "vendor": "",
            "total_spend": 0.0,
            "invoice_count": 0,
        }
    )

    for invoice in invoices:

        vendor = (
            invoice.get("vendor")
            or "Unknown"
        )

        vendors[vendor]["vendor"] = vendor

        vendors[vendor]["invoice_count"] += 1

        vendors[vendor]["total_spend"] += (
            safe_float(
                invoice.get(
                    "total_due"
                )
            )
        )

    rows = list(vendors.values())

    rows.sort(
        key=lambda row:
        row["total_spend"],
        reverse=True,
    )

    return rows


def purchased_item_summary(
    invoices: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Spending grouped by purchased item.
    """

    items = defaultdict(
        lambda: {
            "description": "",
            "quantity": 0,
            "spend": 0,
        }
    )

    for invoice in invoices:

        for item in invoice.get(
            "line_items",
            [],
        ):

            description = (
                item.get(
                    "description"
                )
                or ""
            ).strip()

            if not description:
                continue

            items[
                description
            ]["description"] = (
                description
            )

            items[
                description
            ]["quantity"] += (
                safe_float(
                    item.get(
                        "quantity"
                    )
                )
            )

            items[
                description
            ]["spend"] += (
                safe_float(
                    item.get(
                        "line_total"
                    )
                )
            )

    rows = list(items.values())

    rows.sort(
        key=lambda row:
        row["spend"],
        reverse=True,
    )

    return rows

def monthly_spending(
    invoices: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Spending grouped by month.
    """

    months = defaultdict(
        lambda: {
            "month": "",
            "invoice_count": 0,
            "total_spend": 0.0,
        }
    )

    for invoice in invoices:

        date = parse_invoice_date(
            invoice.get("invoice_date")
        )

        if not date:
            continue

        key = date.strftime("%Y-%m")

        months[key]["month"] = key
        months[key]["invoice_count"] += 1
        months[key]["total_spend"] += safe_float(
            invoice.get("total_due")
        )

    rows = list(months.values())

    rows.sort(
        key=lambda row: row["month"]
    )

    return rows


def vendor_growth(
    invoices: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Compare vendor spending month-to-month.
    """

    vendor_months = defaultdict(
        lambda: defaultdict(float)
    )

    for invoice in invoices:

        vendor = (
            invoice.get("vendor")
            or "Unknown"
        )

        date = parse_invoice_date(
            invoice.get("invoice_date")
        )

        if not date:
            continue

        month = date.strftime("%Y-%m")

        vendor_months[vendor][month] += safe_float(
            invoice.get("total_due")
        )

    report = []

    for vendor, history in vendor_months.items():

        ordered = sorted(history.items())

        if len(ordered) < 2:
            continue

        previous = ordered[-2][1]
        current = ordered[-1][1]

        change = current - previous

        percent = 0

        if previous > 0:
            percent = (
                change / previous
            ) * 100

        report.append(
            {
                "vendor": vendor,
                "previous_month": round(
                    previous,
                    2,
                ),
                "current_month": round(
                    current,
                    2,
                ),
                "change": round(
                    change,
                    2,
                ),
                "percent_change": round(
                    percent,
                    2,
                ),
            }
        )

    report.sort(
        key=lambda row:
        abs(
            row["percent_change"]
        ),
        reverse=True,
    )

    return report


def duplicate_vendor_check(
    invoices: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Look for duplicate vendor + invoice numbers.
    """

    seen = {}

    duplicates = []

    for invoice in invoices:

        key = (
            (
                invoice.get("vendor")
                or ""
            ).lower(),
            (
                invoice.get(
                    "invoice_number"
                )
                or ""
            ).lower(),
        )

        if key in seen:

            duplicates.append(
                invoice
            )

        else:

            seen[key] = invoice

    return duplicates


def largest_vendors(
    invoices: List[Dict[str, Any]],
    limit: int = 5,
) -> List[Dict[str, Any]]:

    return vendor_summary(
        invoices
    )[:limit]


def largest_products(
    invoices: List[Dict[str, Any]],
    limit: int = 5,
) -> List[Dict[str, Any]]:

    return purchased_item_summary(
        invoices
    )[:limit]


def executive_highlights(
    invoices: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Create a structured collection of
    executive facts.

    GPT will eventually turn these into
    a narrative report.
    """

    vendors = largest_vendors(
        invoices
    )

    products = largest_products(
        invoices
    )

    monthly = monthly_spending(
        invoices
    )

    validation = validation_summary(
        invoices
    )

    largest = largest_invoice(
        invoices
    )

    duplicates = duplicate_vendor_check(
        invoices
    )

    return {

        "invoice_count":
            len(invoices),

        "total_spend":
            total_spending(
                invoices
            ),

        "average_invoice":
            average_invoice(
                invoices
            ),

        "largest_invoice":
            largest,

        "validation":
            validation,

        "top_vendor":
            vendors[0]
            if vendors
            else None,

        "top_vendors":
            vendors,

        "top_products":
            products,

        "monthly_spending":
            monthly,

        "vendor_growth":
            vendor_growth(
                invoices
            ),

        "duplicate_count":
            len(
                duplicates
            ),

        "duplicates":
            duplicates,
    }

import json
import os

from openai import OpenAI


def build_executive_prompt(
    executive_data: Dict[str, Any],
) -> str:
    """
    Build a professional executive reporting prompt.
    """

    return f"""
You are the Chief Financial Officer of a professional sports organization.

Your audience is the Finance Director and Executive Leadership Team.

Using ONLY the facts provided below, write a polished executive report.

Requirements:

- Do NOT invent statistics.
- Reference actual numbers from the data.
- Write professionally.
- Sound like Deloitte, PwC, EY, or KPMG.
- Do not use bullet points except in the Recommendations section.
- Write in complete paragraphs.

The report should contain exactly these sections:

# Executive Summary

Provide an overview of invoice activity and overall spending.

# Vendor Analysis

Discuss vendor concentration, major suppliers, and purchasing patterns.

# Purchasing Analysis

Discuss frequently purchased products and purchasing behavior.

# Financial Risks

Identify review items, duplicate invoices, concentration risk, or unusual patterns.

# Recommendations

Provide 4-6 practical recommendations that management could act on immediately.

Financial Data:

{json.dumps(executive_data, indent=4, default=str)}
"""


def generate_ai_summary(
    executive_data: Dict[str, Any],
) -> str:
    """
    Generate an executive narrative.
    """

    api_key = os.getenv(
        "OPENAI_API_KEY"
    )

    if not api_key:

        return (
            "OpenAI API key not configured."
        )

    client = OpenAI(
        api_key=api_key,
    )

    prompt = build_executive_prompt(
        executive_data,
    )

    response = client.chat.completions.create(

        model="gpt-4o-mini",

        temperature=0.3,

        messages=[
            {
                "role": "system",
                "content":
                (
                    "You are a professional CFO "
                    "creating executive reports."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
    )

    return (
        response
        .choices[0]
        .message
        .content
    )


def build_full_executive_report(
    database_path: Path,
) -> Dict[str, Any]:
    """
    Main function used by the application.
    """

    invoices = load_invoice_data(
        database_path,
    )

    facts = executive_highlights(
        invoices,
    )

    report = generate_ai_summary(
        facts,
    )

    return {
        "facts": facts,
        "report": report,
    }