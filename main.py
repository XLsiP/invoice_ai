from pathlib import Path

from src.ai_parser import extract_invoice_fields_with_ai
from src.excel_export import export_invoices_to_excel
from src.parser import extract_invoice_fields
from src.pdf_reader import extract_text_from_pdf

def main() -> None:
    invoice_folder = Path("invoices")
    output_path = Path("excel/invoice_report.xlsx")
    pdf_files = list(invoice_folder.glob("*.pdf"))

    if not pdf_files:
        print("No PDF invoices found")
        return
    print(f"Found {len(pdf_files)} invoice(s).\n")

    all_invoices_data = []

    for pdf_path in pdf_files:
        print(f"Processing: {pdf_path.name}")

    text = extract_text_from_pdf(pdf_path)

    try:
        invoice_data = extract_invoice_fields_with_ai(text)
        print("✅ Parser used: AI")

    except Exception as error:
        print(f"❌ AI parser failed: {error}")
        print("⚠️ Falling back to regex parser.")

        invoice_data = extract_invoice_fields(text)

    all_invoices_data.append(invoice_data)




    export_invoices_to_excel(all_invoices_data, output_path)

    print(f"\nExcel report created: {output_path}")



if __name__ == "__main__":
    main()