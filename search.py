"""
Legacy CLI entry point — predates the Streamlit app (app.py).

Command-line search over the invoice database. The Streamlit app's
Database page covers this same search interactively now, so this script
is kept only as a scriptable/automatable alternative.
"""

import sys
from pathlib import Path

# This file lives in scripts/, one level below the repo root, so the repo
# root needs to be added to sys.path for `from src...` imports to resolve
# regardless of the current working directory it's run from.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.database import get_all_invoices, search_invoices


def print_invoice(invoice: dict) -> None:
    """Display one stored invoice in a readable format."""

    print("-" * 50)
    print(f"Database ID: {invoice.get('id')}")
    print(f"Vendor: {invoice.get('vendor')}")
    print(f"Invoice Number: {invoice.get('invoice_number')}")
    print(f"Invoice Date: {invoice.get('invoice_date')}")
    print(f"Total Due: ${invoice.get('total_due') or 0:.2f}")
    print(f"Status: {invoice.get('validation_status')}")
    print(f"Source File: {invoice.get('source_file')}")


def main() -> None:
    database_path = Path(__file__).resolve().parent.parent / "data" / "invoices.db"

    search_term = input(
        "Search by vendor, invoice number, or filename "
        "(press Enter for all): "
    ).strip()

    if search_term:
        invoices = search_invoices(database_path, search_term)
    else:
        invoices = get_all_invoices(database_path)

    if not invoices:
        print("No matching invoices found.")
        return

    print(f"\nFound {len(invoices)} invoice(s).")

    for invoice in invoices:
        print_invoice(invoice)


if __name__ == "__main__":
    main()