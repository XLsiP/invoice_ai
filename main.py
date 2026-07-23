from pathlib import Path

from src.parser import extract_invoice_fields
from src.pdf_reader import extract_text_from_pdf

def main() -> None:
    invoice_folder = Path("invoices")
    pdf_files = list(invoice_folder.glob("*.pdf"))

    if not pdf_files:
        print("No PDF invoices found")
        return
    print(f"Found {len(pdf_files)} invoice(s).\n")

    for pdf_path in pdf_files:
        print(f"Reading invoice: {pdf_path.name}")
        text = extract_text_from_pdf(pdf_path)
        invoice_data = extract_invoice_fields(text)

    print("Extracted Invoice Data")
    print("="* 30)

    for field, value in invoice_data.items():
        print(f'{field}: {value}')

if __name__ == "__main__":
    main()