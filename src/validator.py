from typing import Any, Dict, List


def validate_invoice(invoice: Dict[str, Any]) -> Dict[str, Any]:
    """Validate extracted invoice data and return validation results."""

    errors: List[str] = []

    vendor = invoice.get("vendor")
    invoice_number = invoice.get("invoice_number")
    subtotal = invoice.get("subtotal")
    tax = invoice.get("tax")
    shipping = invoice.get("shipping")
    total_due = invoice.get("total_due")

    if not vendor:
        errors.append("Vendor is missing.")

    if not invoice_number:
        errors.append("Invoice number is missing.")

    if total_due is None:
        errors.append("Total due is missing.")

    if subtotal is not None and total_due is not None:
        calculated_total = subtotal + (tax or 0) + (shipping or 0)

        if abs(calculated_total - total_due) > 0.01:
            errors.append(
                f"Total mismatch: calculated ${calculated_total:.2f}, "
                f"but invoice total is ${total_due:.2f}."
            )

    return {
        "is_valid": len(errors) == 0,
        "errors": errors,
    }