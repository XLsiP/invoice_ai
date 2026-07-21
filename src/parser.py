import re 

def extract_invoice_fields(text: str) -> dict:
    """
    Extracts invoice fields from the given text.

    Parameters:
        text: The text extracted from the PDF.
    Returns:
        A dictionary containing the extracted invoice fields.
    """
    vendor_match = re.search(
        r'Vendor:\s*(.+)',
        text,
        re.IGNORECASE
    )

    invoice_number_match = re.search(
        r'Invoice Number:\s*(.+)',
        text,
        re.IGNORECASE
    )

    invoice_date_match = re.search(
        r'Invoice Date:\s*(.+)',
        text,
        re.IGNORECASE
    )

    total_due_match = re.search(
        r'Total Due:\s*\$?([\d,]+\.\d{2})',
        text,
        re.IGNORECASE
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
        "total_due": (
            float(total_due_match.group(1).replace(",", ""))
            if total_due_match
            else None
        ),
    }