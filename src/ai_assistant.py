import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.database import (
    get_all_invoices,
    get_vendor_statistics,
    search_invoices,
)


DEFAULT_LIMIT = 5


def safe_float(value: Any) -> float:
    """Convert a value to float without raising an exception."""

    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def normalize_text(value: Any) -> str:
    """Normalize text for case-insensitive matching."""

    if value is None:
        return ""

    return str(value).strip().lower()


def format_money(value: Any) -> str:
    """Format a value as U.S. currency."""

    return f"${safe_float(value):,.2f}"


def extract_requested_limit(
    question: str,
    default: int = DEFAULT_LIMIT,
) -> int:
    """Extract a requested top-N value from a question."""

    match = re.search(
        r"\btop\s+(\d+)\b",
        question,
        re.IGNORECASE,
    )

    if not match:
        return default

    try:
        return max(1, min(int(match.group(1)), 25))
    except ValueError:
        return default


def classify_question(question: str) -> str:
    """Classify a question into a supported intent."""

    normalized = normalize_text(question)

    if not normalized:
        return "empty"

    if any(
        phrase in normalized
        for phrase in [
            "top vendor",
            "largest vendor",
            "biggest vendor",
            "spend the most with",
            "most money with",
            "highest vendor",
        ]
    ):
        return "top_vendors"

    if any(
        phrase in normalized
        for phrase in [
            "top product",
            "top item",
            "most purchased",
            "most bought",
            "highest spend item",
            "highest-spend item",
            "purchased products",
        ]
    ):
        return "top_products"

    if any(
        phrase in normalized
        for phrase in [
            "how much have we spent",
            "total spend",
            "total spending",
            "overall spend",
            "overall spending",
            "spending summary",
        ]
    ):
        return "overall_summary"

    if any(
        phrase in normalized
        for phrase in [
            "show every invoice containing",
            "show invoices containing",
            "find invoices containing",
            "search invoices for",
            "invoice containing",
            "invoices with",
        ]
    ):
        return "item_search"

    if any(
        phrase in normalized
        for phrase in [
            "tell me about",
            "vendor summary",
            "vendor details",
            "how much did we spend with",
            "spend with",
        ]
    ):
        return "vendor_lookup"

    if any(
        phrase in normalized
        for phrase in [
            "this month",
            "current month",
            "monthly spend",
            "monthly spending",
        ]
    ):
        return "current_month_summary"

    if any(
        phrase in normalized
        for phrase in [
            "needs review",
            "need review",
            "invalid invoice",
            "validation issue",
            "validation error",
        ]
    ):
        return "review_queue"

    return "general_search"


def get_overall_summary(database_path: Path) -> Dict[str, Any]:
    """Return overall invoice metrics."""

    invoices = get_all_invoices(database_path)

    total_spend = sum(
        safe_float(invoice.get("total_due"))
        for invoice in invoices
    )

    valid_count = sum(
        1
        for invoice in invoices
        if invoice.get("validation_status") == "Valid"
    )

    vendors = {
        normalize_text(invoice.get("vendor"))
        for invoice in invoices
        if normalize_text(invoice.get("vendor"))
    }

    line_item_count = sum(
        len(invoice.get("line_items", []) or [])
        for invoice in invoices
    )

    average_invoice = (
        total_spend / len(invoices)
        if invoices
        else 0.0
    )

    return {
        "invoice_count": len(invoices),
        "vendor_count": len(vendors),
        "line_item_count": line_item_count,
        "total_spend": round(total_spend, 2),
        "average_invoice": round(average_invoice, 2),
        "valid_count": valid_count,
        "needs_review_count": len(invoices) - valid_count,
    }


def get_top_vendors(
    database_path: Path,
    limit: int = DEFAULT_LIMIT,
) -> List[Dict[str, Any]]:
    """Return the highest-spend vendors."""

    vendors = get_vendor_statistics(database_path)
    clean_rows = []

    for vendor in vendors[:limit]:
        clean_rows.append(
            {
                "vendor": vendor.get("vendor"),
                "invoice_count": int(
                    vendor.get("invoice_count") or 0
                ),
                "total_spend": safe_float(
                    vendor.get("total_spend")
                ),
                "average_invoice": safe_float(
                    vendor.get("average_invoice")
                ),
                "largest_invoice": safe_float(
                    vendor.get("largest_invoice")
                ),
                "first_invoice_date": vendor.get(
                    "first_invoice_date"
                ),
                "last_invoice_date": vendor.get(
                    "last_invoice_date"
                ),
            }
        )

    return clean_rows


def get_top_products(
    database_path: Path,
    limit: int = DEFAULT_LIMIT,
) -> List[Dict[str, Any]]:
    """Return the highest-spend purchased products."""

    invoices = get_all_invoices(database_path)
    grouped: Dict[str, Dict[str, Any]] = {}

    for invoice in invoices:
        vendor = invoice.get("vendor") or "Unknown vendor"

        for item in invoice.get("line_items", []) or []:
            description = str(
                item.get("description") or ""
            ).strip()

            if not description:
                continue

            key = normalize_text(description)

            if key not in grouped:
                grouped[key] = {
                    "description": description,
                    "total_quantity": 0.0,
                    "total_spend": 0.0,
                    "invoice_count": 0,
                    "vendors": set(),
                }

            grouped[key]["total_quantity"] += safe_float(
                item.get("quantity")
            )
            grouped[key]["total_spend"] += safe_float(
                item.get("line_total")
            )
            grouped[key]["invoice_count"] += 1
            grouped[key]["vendors"].add(vendor)

    products = []

    for product in grouped.values():
        products.append(
            {
                "description": product["description"],
                "total_quantity": round(
                    product["total_quantity"],
                    2,
                ),
                "total_spend": round(
                    product["total_spend"],
                    2,
                ),
                "invoice_count": product["invoice_count"],
                "vendor_count": len(product["vendors"]),
            }
        )

    products.sort(
        key=lambda item: item["total_spend"],
        reverse=True,
    )

    return products[:limit]


def search_items(
    database_path: Path,
    search_term: str,
) -> List[Dict[str, Any]]:
    """Find invoice line items matching a search term."""

    normalized_term = normalize_text(search_term)

    if not normalized_term:
        return []

    results = []

    for invoice in get_all_invoices(database_path):
        for item in invoice.get("line_items", []) or []:
            description = str(
                item.get("description") or ""
            ).strip()

            if normalized_term not in normalize_text(description):
                continue

            results.append(
                {
                    "invoice_id": invoice.get("id"),
                    "vendor": invoice.get("vendor"),
                    "invoice_number": invoice.get(
                        "invoice_number"
                    ),
                    "invoice_date": invoice.get("invoice_date"),
                    "source_file": invoice.get("source_file"),
                    "description": description,
                    "quantity": safe_float(
                        item.get("quantity")
                    ),
                    "unit_price": safe_float(
                        item.get("unit_price")
                    ),
                    "line_total": safe_float(
                        item.get("line_total")
                    ),
                }
            )

    results.sort(
        key=lambda row: (
            row.get("invoice_date") or "",
            row.get("invoice_id") or 0,
        ),
        reverse=True,
    )

    return results


def get_vendor_summary(
    database_path: Path,
    vendor_query: str,
) -> Optional[Dict[str, Any]]:
    """Return invoice and item details for the closest vendor match."""

    normalized_query = normalize_text(vendor_query)

    if not normalized_query:
        return None

    invoices = get_all_invoices(database_path)

    matching_invoices = [
        invoice
        for invoice in invoices
        if normalized_query in normalize_text(
            invoice.get("vendor")
        )
    ]

    if not matching_invoices:
        return None

    vendor_name = (
        matching_invoices[0].get("vendor")
        or vendor_query
    )

    total_spend = sum(
        safe_float(invoice.get("total_due"))
        for invoice in matching_invoices
    )

    largest_invoice = max(
        (
            safe_float(invoice.get("total_due"))
            for invoice in matching_invoices
        ),
        default=0.0,
    )

    all_items = []

    for invoice in matching_invoices:
        all_items.extend(
            invoice.get("line_items", []) or []
        )

    item_spend: Dict[str, float] = {}

    for item in all_items:
        description = str(
            item.get("description") or ""
        ).strip()

        if not description:
            continue

        item_spend[description] = (
            item_spend.get(description, 0.0)
            + safe_float(item.get("line_total"))
        )

    top_items = sorted(
        item_spend.items(),
        key=lambda pair: pair[1],
        reverse=True,
    )[:5]

    return {
        "vendor": vendor_name,
        "invoice_count": len(matching_invoices),
        "total_spend": round(total_spend, 2),
        "average_invoice": round(
            total_spend / len(matching_invoices),
            2,
        ),
        "largest_invoice": round(
            largest_invoice,
            2,
        ),
        "top_items": [
            {
                "description": description,
                "total_spend": round(spend, 2),
            }
            for description, spend in top_items
        ],
        "invoices": matching_invoices,
    }


def get_current_month_summary(
    database_path: Path,
) -> Dict[str, Any]:
    """Return spending metrics for the current calendar month."""

    now = datetime.now()
    current_prefix = now.strftime("%Y-%m")

    invoices = []

    for invoice in get_all_invoices(database_path):
        invoice_date = str(
            invoice.get("invoice_date") or ""
        )

        if invoice_date.startswith(current_prefix):
            invoices.append(invoice)

    total_spend = sum(
        safe_float(invoice.get("total_due"))
        for invoice in invoices
    )

    return {
        "month": now.strftime("%B %Y"),
        "invoice_count": len(invoices),
        "total_spend": round(total_spend, 2),
        "average_invoice": round(
            total_spend / len(invoices),
            2,
        )
        if invoices
        else 0.0,
        "invoices": invoices,
    }


def get_review_queue(
    database_path: Path,
) -> List[Dict[str, Any]]:
    """Return invoices that require manual review."""

    return [
        invoice
        for invoice in get_all_invoices(database_path)
        if invoice.get("validation_status") != "Valid"
    ]


def extract_search_term(
    question: str,
    intent: str,
) -> str:
    """Extract a vendor or item term from a natural-language question."""

    cleaned = question.strip().rstrip("?.!")
    patterns: List[Tuple[str, str]] = []

    if intent == "item_search":
        patterns = [
            (r"show every invoice containing\s+(.+)", "item"),
            (r"show invoices containing\s+(.+)", "item"),
            (r"find invoices containing\s+(.+)", "item"),
            (r"search invoices for\s+(.+)", "item"),
            (r"invoices with\s+(.+)", "item"),
        ]

    elif intent == "vendor_lookup":
        patterns = [
            (r"tell me about\s+(.+)", "vendor"),
            (r"vendor summary for\s+(.+)", "vendor"),
            (r"how much did we spend with\s+(.+)", "vendor"),
            (r"spend with\s+(.+)", "vendor"),
        ]

    for pattern, _ in patterns:
        match = re.search(
            pattern,
            cleaned,
            re.IGNORECASE,
        )

        if match:
            return match.group(1).strip()

    return cleaned


def route_question(
    database_path: Path,
    question: str,
) -> Dict[str, Any]:
    """Route a question to the matching database-backed handler."""

    intent = classify_question(question)
    limit = extract_requested_limit(question)

    if intent == "empty":
        return {
            "intent": intent,
            "success": False,
            "message": "Enter a question about your invoices.",
            "data": None,
        }

    if intent == "top_vendors":
        data = get_top_vendors(
            database_path,
            limit=limit,
        )

    elif intent == "top_products":
        data = get_top_products(
            database_path,
            limit=limit,
        )

    elif intent == "overall_summary":
        data = get_overall_summary(database_path)

    elif intent == "item_search":
        search_term = extract_search_term(
            question,
            intent,
        )
        data = {
            "search_term": search_term,
            "matches": search_items(
                database_path,
                search_term,
            ),
        }

    elif intent == "vendor_lookup":
        vendor_query = extract_search_term(
            question,
            intent,
        )
        data = get_vendor_summary(
            database_path,
            vendor_query,
        )

    elif intent == "current_month_summary":
        data = get_current_month_summary(
            database_path
        )

    elif intent == "review_queue":
        data = get_review_queue(database_path)

    else:
        data = {
            "search_term": question.strip(),
            "matches": search_invoices(
                database_path,
                question.strip(),
            ),
        }

    return {
        "intent": intent,
        "success": True,
        "message": None,
        "data": data,
    }


def answer_question(
    database_path: Path,
    question: str,
) -> Dict[str, Any]:
    """Public entry point for the rule-based assistant foundation."""

    try:
        return route_question(
            database_path,
            question,
        )

    except Exception as error:
        return {
            "intent": "error",
            "success": False,
            "message": str(error),
            "data": None,
        }