import re


def extract_invoice_fields(text: str) -> dict:
    """Extract common invoice fields from raw invoice text."""

    vendor_match = re.search(
        r"Vendor:\s*(.+)",
        text,
        re.IGNORECASE,
    )

    invoice_number_match = re.search(
        r"Invoice Number:\s*(.+)",
        text,
        re.IGNORECASE,
    )

    invoice_date_match = re.search(
        r"Invoice Date:\s*(.+)",
        text,
        re.IGNORECASE,
    )

    due_date_match = re.search(
        r"Due Date:\s*(.+)",
        text,
        re.IGNORECASE,
    )

    description_match = re.search(
        r"Description:\s*(.+)",
        text,
        re.IGNORECASE,
    )

    subtotal_match = re.search(
        r"Subtotal:\s*\$?([\d,]+\.\d{2})",
        text,
        re.IGNORECASE,
    )

    tax_match = re.search(
        r"Tax:\s*\$?([\d,]+\.\d{2})",
        text,
        re.IGNORECASE,
    )

    shipping_match = re.search(
        r"Shipping:\s*\$?([\d,]+\.\d{2})",
        text,
        re.IGNORECASE,
    )

    total_due_match = re.search(
        r"Total Due:\s*\$?([\d,]+\.\d{2})",
        text,
        re.IGNORECASE,
    )

    return {
        "vendor": vendor_match.group(1).strip() if vendor_match else None,
        "invoice_number": (
            invoice_number_match.group(1).strip()
            if invoice_number_match
            else None
        ),
        "invoice_date": (
            invoice_date_match.group(1).strip()
            if invoice_date_match
            else None
        ),
        "due_date": (
            due_date_match.group(1).strip()
            if due_date_match
            else None
        ),
        "description": (
            description_match.group(1).strip()
            if description_match
            else None
        ),
        "subtotal": parse_money(subtotal_match),
        "tax": parse_money(tax_match),
        "shipping": parse_money(shipping_match),
        "total_due": parse_money(total_due_match),
    }


def parse_money(match: re.Match | None) -> float | None:
    """Convert a matched currency value into a float."""
    if match is None:
        return None

    return float(match.group(1).replace(",", ""))