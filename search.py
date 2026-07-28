from pathlib import Path

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
    database_path = Path("data/invoices.db")

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