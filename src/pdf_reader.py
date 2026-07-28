from pathlib import Path

import fitz

from src.ocr import extract_text_from_image, extract_text_with_ocr


MINIMUM_PAGE_TEXT_LENGTH = 30
SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}


def extract_text_from_file(file_path: Path) -> str:
    """Extract text from a supported PDF or image file."""

    if not file_path.exists():
        raise FileNotFoundError(
            f"Could not find file: {file_path}"
        )

    extension = file_path.suffix.lower()

    if extension == ".pdf":
        return extract_text_from_pdf(file_path)

    if extension in SUPPORTED_IMAGE_EXTENSIONS:
        print(f"Running OCR on image: {file_path.name}")

        return extract_text_from_image(file_path)

    raise ValueError(
        f"Unsupported file type: {extension}. "
        "Supported formats are PDF, PNG, JPG, and JPEG."
    )


def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract text from a PDF, using OCR when necessary."""

    document = fitz.open(pdf_path)
    pages = []

    try:
        for page_number, page in enumerate(document, start=1):
            page_text = page.get_text().strip()

            if len(page_text) < MINIMUM_PAGE_TEXT_LENGTH:
                print(
                    f"Page {page_number} has little or no "
                    "selectable text. Running OCR..."
                )

                page_text = extract_text_with_ocr(page)

            pages.append(page_text)

    finally:
        document.close()

    return "\n".join(pages)