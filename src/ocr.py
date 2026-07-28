from pathlib import Path

import fitz


def extract_text_from_image(image_path: Path) -> str:
    """Extract text from a PNG, JPG, or JPEG image using OCR."""

    image_document = fitz.open(image_path)

    try:
        page = image_document[0]

        text_page = page.get_textpage_ocr(
            language="eng",
            dpi=300,
            full=True,
        )

        return page.get_text(
            "text",
            textpage=text_page,
        ).strip()

    finally:
        image_document.close()


def extract_text_with_ocr(page: fitz.Page) -> str:
    """Extract text from an image-based PDF page using OCR."""

    text_page = page.get_textpage_ocr(
        language="eng",
        dpi=300,
        full=True,
    )

    return page.get_text(
        "text",
        textpage=text_page,
    ).strip()