from pathlib import Path
import fitz # PyMuPDF

def extract_text_from_pdf(pdf_path: Path) -> str:

    """
    Extract all embedded text from a PDF.

    Parameters:
        pdf_path: Path to the PDF file.

    Returns:
        A single string containing all text from every page.
    """
    #validate file
    if not pdf_path.exists():
        raise FileNotFoundError(f"Could not find PDF:{pdf_path} ")
    
    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError(f"Expected a PDF file, but got: {pdf_path.suffix}")
    #Open the document
    document = fitz.open(pdf_path)
    pages = []

    #Read every page and extract text
    for page in document:
        page_text = page.get_text()
        pages.append(page_text)
    document.close()

    #return one giant string with all the text from the PDF
    return "\n".join(pages)