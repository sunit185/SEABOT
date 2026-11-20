"""
ocr.py — Tesseract OCR for scanned PDF pages via PyMuPDF rendering.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def ocr_page(pdf_path: str, page_num: int, dpi: int = 150) -> str:
    """
    OCR a single page of a PDF and return extracted text.

    Parameters
    ----------
    pdf_path : str
        Path to the PDF file.
    page_num : int
        0-indexed page number.
    dpi : int
        Resolution used for rendering the page to a raster image.

    Returns
    -------
    str
        Extracted text, or "" on any failure.
    """
    try:
        import fitz  # PyMuPDF
        import pytesseract
        from PIL import Image
        import io

        doc = fitz.open(pdf_path)
        try:
            if page_num < 0 or page_num >= len(doc):
                logger.warning(
                    "ocr_page: page_num %d out of range for %s", page_num, pdf_path
                )
                return ""

            page = doc[page_num]
            zoom = dpi / 72.0
            mat = fitz.Matrix(zoom, zoom)
            pixmap = page.get_pixmap(matrix=mat, alpha=False)

            # Convert pixmap bytes to PIL Image
            img_bytes = pixmap.tobytes("png")
            image = Image.open(io.BytesIO(img_bytes))

            text: str = pytesseract.image_to_string(image, lang="eng")
            return text
        finally:
            doc.close()

    except Exception as exc:
        logger.error("ocr_page failed for %s page %d: %s", pdf_path, page_num, exc)
        return ""
