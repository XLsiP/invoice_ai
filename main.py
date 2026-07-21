from pathlib import Path
from src.pdf_reader import extract_text_from_pdf

def main():
    pdf_path = Path("invoices/sample_invoice.pdf")
    print("Reading invoice.....\n")
    text = extract_text_from_pdf(pdf_path)
    print(text)

if __name__ == "__main__":
    main()