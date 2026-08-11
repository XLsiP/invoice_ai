import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

from src import analytics
from src.database import get_all_invoices, search_invoices

DEFAULT_LIMIT = 5


def extract_requested_limit(question: str, default: int = DEFAULT_LIMIT) -> int:
    """Extract a requested top-N value from a question."""

    match = re.search(r"\btop\s+(\d+)\b", question, re.IGNORECASE)

    if not match:
        return default

    try:
        return max(1, min(int(match.group(1)), 25))
    except ValueError:
        return default


def classify_question(question: str) -> str:
    """Classify a question into a supported intent."""

    normalized = analytics.normalize_text(question)

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


def extract_search_term(question: str, intent: str) -> str:
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
        match = re.search(pattern, cleaned, re.IGNORECASE)

        if match:
            return match.group(1).strip()

    return cleaned


def route_question(database_path: Path, question: str) -> Dict[str, Any]:
    """Route a question to the matching analytics-backed handler."""

    intent = classify_question(question)
    limit = extract_requested_limit(question)

    if intent == "empty":
        return {
            "intent": intent,
            "success": False,
            "message": "Enter a question about your invoices.",
            "data": None,
        }

    # Every remaining intent works off the same loaded invoice list, so
    # there is exactly one database round trip per question.
    invoices = get_all_invoices(database_path)

    if intent == "top_vendors":
        data = analytics.vendor_summary(invoices, limit=limit)

    elif intent == "top_products":
        data = analytics.purchased_item_summary(invoices, limit=limit)

    elif intent == "overall_summary":
        data = analytics.overall_summary(invoices)

    elif intent == "item_search":
        search_term = extract_search_term(question, intent)
        data = {
            "search_term": search_term,
            "matches": analytics.search_items(invoices, search_term),
        }

    elif intent == "vendor_lookup":
        vendor_query = extract_search_term(question, intent)
        data = analytics.vendor_lookup(invoices, vendor_query)

    elif intent == "current_month_summary":
        data = analytics.current_month_summary(invoices)

    elif intent == "review_queue":
        data = analytics.review_queue(invoices)

    else:
        data = {
            "search_term": question.strip(),
            "matches": search_invoices(database_path, question.strip()),
        }

    return {
        "intent": intent,
        "success": True,
        "message": None,
        "data": data,
    }


def answer_question(database_path: Path, question: str) -> Dict[str, Any]:
    """Public entry point for the natural-language assistant."""

    try:
        return route_question(database_path, question)

    except Exception as error:
        return {
            "intent": "error",
            "success": False,
            "message": str(error),
            "data": None,
        }