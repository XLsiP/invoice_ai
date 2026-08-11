import json
import os
from typing import Any, Dict, List

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


def safe_float(value: Any) -> float:
    """Safely convert any value into a float."""

    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def clean_line_items(
    items: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Clean AI output before saving."""

    cleaned = []

    for item in items:
        description = str(
            item.get("description", "")
        ).strip()

        if not description:
            continue

        quantity = safe_float(
            item.get("quantity")
        )

        unit_price = safe_float(
            item.get("unit_price")
        )

        line_total = safe_float(
            item.get("line_total")
        )

        if line_total == 0 and quantity and unit_price:
            line_total = quantity * unit_price

        cleaned.append(
            {
                "description": description,
                "quantity": quantity,
                "unit_price": unit_price,
                "line_total": line_total,
            }
        )

    return cleaned


def extract_line_items_with_ai(
    invoice_text: str,
) -> List[Dict[str, Any]]:
    """Extract purchased products or services from invoice text."""

    if not invoice_text.strip():
        return []

    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY is missing. "
            "Set it in your terminal before running the app."
        )

    client = OpenAI(
        api_key=api_key
    )

    prompt = f"""
You are an accounts payable specialist.

Extract ONLY purchased products or services.

DO NOT include:
- Subtotal
- Tax
- Shipping
- Discount
- Balance
- Grand Total
- Invoice Total
- Payment
- Amount Due

Return only valid JSON in this format:

{{
    "line_items": [
        {{
            "description": "Copy Paper",
            "quantity": 5,
            "unit_price": 7.99,
            "line_total": 39.95
        }}
    ]
}}

Invoice text:

{invoice_text[:30000]}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={
            "type": "json_object"
        },
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
    )

    content = response.choices[0].message.content

    if not content:
        return []

    data = json.loads(content)

    return clean_line_items(
        data.get("line_items", [])
    )