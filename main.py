from pathlib import Path

from src.database import initialize_database, save_invoice
from src.ai_parser import extract_invoice_fields_with_ai
from src.excel_export import export_invoices_to_excel
from src.parser import extract_invoice_fields
from src.pdf_reader import extract_text_from_pdf
from src.validator import validate_invoice


def main() -> None:
    invoices_folder = Path("invoices")
    output_path = Path("excel/invoice_report.xlsx")
    database_path = Path("data/invoices.db")

    initialize_database(database_path)

    pdf_files = list(invoices_folder.glob("*.pdf"))

    if not pdf_files:
        print("No PDF invoices found.")
        return

    print(f"Found {len(pdf_files)} invoice(s).\n")

    all_invoice_data = []

    for pdf_path in pdf_files:
        print("=" * 50)
        print(f"Processing: {pdf_path.name}")

        # Step 1: Read the PDF
        text = extract_text_from_pdf(pdf_path)

        # Step 2: Try AI parser first
        try:
            invoice_data = extract_invoice_fields_with_ai(text)
            print("✅ Parser used: AI")

        # Step 3: Fall back to regex if AI fails
        except Exception as error:
            print(f"❌ AI parser failed: {error}")
            print("⚠️ Falling back to regex parser.")

            invoice_data = extract_invoice_fields(text)

        # Step 4: Validate the extracted data
        
        validation_result = validate_invoice(invoice_data)

        invoice_data["validation_status"] = (
            "Valid"
            if validation_result["is_valid"]
            else "Needs Review"
        )

        invoice_data["validation_errors"] = "; ".join(
            validation_result["errors"]
        )

        # Save the source filename
        invoice_data["source_file"] = pdf_path.name

        # Display results in terminal
        print(f"Validation: {invoice_data['validation_status']}")

        if validation_result["errors"]:
            for error in validation_result["errors"]:
                print(f"   • {error}")

        print("\nExtracted Invoice Data")
        print("-" * 30)

        for field, value in invoice_data.items():
            print(f"{field}: {value}")

        print()

        # Add invoice to master list
        all_invoice_data.append(invoice_data)
        save_invoice(database_path, invoice_data)
        print("Saved to database.\n")

    # Step 5: Export everything to Excel
    export_invoices_to_excel(
        all_invoice_data,
        output_path,
    )

    print("=" * 50)
    print("✅ Processing Complete!")
    print(f"Excel report created: {output_path}")


if __name__ == "__main__":
    main()