from pathlib import Path

from src.parser import extract_invoice_fields
from src.pdf_reader import extract_text_from_pdf

def main():
    pdf_path = Path("invoices/sample_invoice.pdf")
    print("Reading invoice.....\n")
    text = extract_text_from_pdf(pdf_path)
    invoice_data = extract_invoice_fields(text)
    print("Extracted Invoice Data")
    print("="* 30)
    for field, value in invoice_data.items():
        print(f'{field}: {value}')

if __name__ == "__main__":
    main()