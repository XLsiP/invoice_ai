from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv
from openai import OpenAI

from src import analytics
from src.database import get_all_invoices

load_dotenv()


def load_invoice_data(database_path: Path) -> List[Dict[str, Any]]:
    """
    Load every invoice.

    This is the single source of truth used throughout executive reporting.
    """

    return get_all_invoices(database_path)


def largest_vendors(
    invoices: List[Dict[str, Any]],
    limit: int = 5,
) -> List[Dict[str, Any]]:

    return analytics.vendor_summary(invoices, limit=limit)


def largest_products(
    invoices: List[Dict[str, Any]],
    limit: int = 5,
) -> List[Dict[str, Any]]:

    return analytics.purchased_item_summary(invoices, limit=limit)


def executive_highlights(invoices: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Create a structured collection of executive facts.

    GPT turns these into a narrative report.
    """

    vendors = largest_vendors(invoices)
    products = largest_products(invoices)
    monthly = analytics.monthly_spending(invoices)
    validation = analytics.validation_summary(invoices)
    duplicates = analytics.duplicate_vendor_check(invoices)

    # The "whole" a purchased-item donut should sum to is total line-item
    # spend, not total invoice spend — invoice totals include tax and
    # shipping, which aren't purchased products, so using them here would
    # inflate the "Other" bucket with non-product dollars.
    total_item_spend = round(
        sum(row["spend"] for row in analytics.purchased_item_summary(invoices)), 2
    )

    return {
        "invoice_count": len(invoices),
        "total_spend": analytics.total_spending(invoices),
        "average_invoice": analytics.average_invoice(invoices),
        "largest_invoice": analytics.largest_invoice(invoices),
        "validation": validation,
        "top_vendor": vendors[0] if vendors else None,
        "top_vendors": vendors,
        "top_products": products,
        "total_item_spend": total_item_spend,
        "monthly_spending": monthly,
        "vendor_growth": analytics.vendor_growth(invoices),
        "duplicate_count": len(duplicates),
        "duplicates": duplicates,
    }


def build_executive_prompt(executive_data: Dict[str, Any]) -> str:
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


def generate_ai_summary(executive_data: Dict[str, Any]) -> str:
    """
    Generate an executive narrative.
    """

    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        return "OpenAI API key not configured."

    client = OpenAI(api_key=api_key)

    prompt = build_executive_prompt(executive_data)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.3,
        messages=[
            {
                "role": "system",
                "content": ("You are a professional CFO creating executive reports."),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
    )

    return response.choices[0].message.content


def build_full_executive_report(database_path: Path) -> Dict[str, Any]:
    """
    Main function used by the application.
    """

    invoices = load_invoice_data(database_path)
    facts = executive_highlights(invoices)
    report = generate_ai_summary(facts)

    return {
        "facts": facts,
        "report": report,
    }