from pathlib import Path
from typing import Any, Dict, List

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.table import Table, TableStyleInfo


HEADERS = [
    "Source File",
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
    "Created At",
]

FIELD_KEYS = [
    "source_file",
    "vendor",
    "invoice_number",
    "invoice_date",
    "due_date",
    "description",
    "subtotal",
    "tax",
    "shipping",
    "total_due",
    "validation_status",
    "validation_errors",
    "created_at",
]


def export_invoices_to_excel(
    invoices: List[Dict[str, Any]],
    output_path: Path,
) -> None:
    """Export invoice records to a readable Excel workbook."""

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Invoices"

    worksheet.append(HEADERS)

    for invoice in invoices:
        worksheet.append(
            [
                invoice.get(field_key)
                for field_key in FIELD_KEYS
            ]
        )

    header_fill = PatternFill(
        fill_type="solid",
        fgColor="F15A24",
    )
    header_font = Font(
        color="FFFFFF",
        bold=True,
    )
    thin_gray = Side(
        style="thin",
        color="D9D9D9",
    )

    for cell in worksheet[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(
            horizontal="center",
            vertical="center",
            wrap_text=True,
        )
        cell.border = Border(
            bottom=thin_gray,
        )

    worksheet.row_dimensions[1].height = 34
    worksheet.freeze_panes = "A2"
    worksheet.auto_filter.ref = worksheet.dimensions

    for column_letter in ["G", "H", "I", "J"]:
        for cell in worksheet[column_letter][1:]:
            cell.number_format = '$#,##0.00'
            cell.alignment = Alignment(
                horizontal="right",
                vertical="top",
            )

    for column_letter in ["A", "B", "C", "D", "E", "F", "K", "L", "M"]:
        for cell in worksheet[column_letter][1:]:
            cell.alignment = Alignment(
                vertical="top",
                wrap_text=True,
            )

    for row in worksheet.iter_rows(
        min_row=2,
        max_row=worksheet.max_row,
    ):
        for cell in row:
            cell.border = Border(
                bottom=thin_gray,
            )

    column_widths = {
        "A": 30,
        "B": 28,
        "C": 20,
        "D": 18,
        "E": 18,
        "F": 48,
        "G": 14,
        "H": 12,
        "I": 12,
        "J": 14,
        "K": 18,
        "L": 48,
        "M": 21,
    }

    for column_letter, width in column_widths.items():
        worksheet.column_dimensions[column_letter].width = width

    for row_number in range(2, worksheet.max_row + 1):
        worksheet.row_dimensions[row_number].height = 36

    if worksheet.max_row >= 2:
        table = Table(
            displayName="InvoicesTable",
            ref=f"A1:M{worksheet.max_row}",
        )

        table.tableStyleInfo = TableStyleInfo(
            name="TableStyleMedium2",
            showFirstColumn=False,
            showLastColumn=False,
            showRowStripes=True,
            showColumnStripes=False,
        )

        worksheet.add_table(table)

    summary = workbook.create_sheet("Summary")

    summary["A1"] = "AP Accounts Payable Ledger"
    summary["A1"].font = Font(
        bold=True,
        size=18,
        color="FFFFFF",
    )
    summary["A1"].fill = header_fill
    summary.merge_cells("A1:D1")

    total_value = sum(
        float(invoice.get("total_due") or 0)
        for invoice in invoices
    )

    valid_count = sum(
        1
        for invoice in invoices
        if invoice.get("validation_status") == "Valid"
    )

    summary["A3"] = "Total invoices"
    summary["B3"] = len(invoices)

    summary["A4"] = "Total invoice value"
    summary["B4"] = total_value
    summary["B4"].number_format = '$#,##0.00'

    summary["A5"] = "Validated invoices"
    summary["B5"] = valid_count

    summary["A6"] = "Needs review"
    summary["B6"] = len(invoices) - valid_count

    summary.column_dimensions["A"].width = 26
    summary.column_dimensions["B"].width = 18

    for row_number in range(3, 7):
        summary[f"A{row_number}"].font = Font(
            bold=True,
        )
        summary[f"A{row_number}"].alignment = Alignment(
            wrap_text=True,
        )

    workbook.save(output_path)