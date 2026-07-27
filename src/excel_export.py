from pathlib import Path
from openpyxl import Workbook

def export_invoices_to_excel(invoices: list[dict], output_path: Path) -> None:
    """Export structured invoice data into an Excel spreadsheet."""
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Invoices"

    headers = [
        "Vendor",
        "Invoice Number",
        "Invoice Date",
        "Due Date",
        "Description",
        "Subtotal",
        "Tax",
        "Shipping",
        "Total Due",
        "Validation Status",
        "Validation Errors",

    ]

    worksheet.append(headers)

    for invoice in invoices:
        worksheet.append(
            [
                invoice.get("vendor"),
                invoice.get("invoice_number"),
                invoice.get("invoice_date"),
                invoice.get("due_date"),
                invoice.get("description"),
                invoice.get("subtotal"),
                invoice.get("tax"),
                invoice.get("shipping"),
                invoice.get("total_due"),
                invoice.get("validation_status"),
                invoice.get("validation_errors"),
            ]
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(output_path)
