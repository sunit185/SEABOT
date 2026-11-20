"""
pdf_parser.py — Parse PDF files using PyMuPDF (fitz).

Returns per-page structured dicts including extracted text, tables as markdown,
section heading detection, diagram detection, scanned-page flags, and bboxes.
"""
from __future__ import annotations

import logging
from typing import Any

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)

# Heuristic: if a page has fewer than this many characters of text, treat it as
# scanned (i.e. image-only) and flag it for OCR.
SCANNED_CHAR_THRESHOLD = 100

# If a page has more than this many vector drawings, consider it a diagram page.
DRAWING_DENSITY_THRESHOLD = 20


def _blocks_to_markdown_table(table_obj: Any) -> str:
    """Convert a PyMuPDF Table object to a Markdown table string."""
    try:
        rows = table_obj.extract()
        if not rows:
            return ""
        lines: list[str] = []
        # Header row
        header = [str(cell) if cell is not None else "" for cell in rows[0]]
        lines.append("| " + " | ".join(header) + " |")
        lines.append("| " + " | ".join(["---"] * len(header)) + " |")
        for row in rows[1:]:
            cells = [str(cell) if cell is not None else "" for cell in row]
            lines.append("| " + " | ".join(cells) + " |")
        return "\n".join(lines)
    except Exception:
        return ""


def _detect_section_heading(block: dict, avg_font_size: float) -> str | None:
    """
    Return the text of a block if it looks like a section heading.

    Criteria:
    - Font size > page average, OR
    - Any span has bold flag (flags & 16 != 0 in PyMuPDF)
    """
    if block.get("type") != 0:  # only text blocks
        return None
    for line in block.get("lines", []):
        for span in line.get("spans", []):
            is_large = span.get("size", 0) > avg_font_size * 1.1
            is_bold = bool(span.get("flags", 0) & 16)
            if (is_large or is_bold) and span.get("text", "").strip():
                return span["text"].strip()
    return None


def _page_average_font_size(page_dict: dict) -> float:
    """Compute the average font size across all spans on the page."""
    sizes: list[float] = []
    for block in page_dict.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                s = span.get("size", 0)
                if s > 0:
                    sizes.append(s)
    return sum(sizes) / len(sizes) if sizes else 12.0


def _page_text_from_dict(page_dict: dict) -> str:
    """Concatenate all text spans from a page dict."""
    parts: list[str] = []
    for block in page_dict.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                t = span.get("text", "")
                if t:
                    parts.append(t)
        parts.append("\n")
    return "".join(parts)


def parse_pdf(file_path: str, doc_id: str, doc_name: str) -> dict[str, Any]:
    """
    Parse a PDF file and return structured page data.

    Returns:
        {
            "pages": list[page_dict],
            "scanned_pages": list[int],   # 0-indexed page numbers
            "diagram_pages": list[int],
        }

    Each page_dict:
        {
            "page_num": int,              # 1-indexed
            "text": str,
            "tables": list[str],          # markdown table strings
            "section_heading": str | None,
            "has_diagram": bool,
            "bbox": [x0, y0, x1, y1],
            "is_scanned": bool,
        }
    """
    pages: list[dict[str, Any]] = []
    scanned_pages: list[int] = []
    diagram_pages: list[int] = []

    doc = fitz.open(file_path)
    try:
        for page_index in range(len(doc)):
            page = doc[page_index]
            page_num = page_index + 1  # 1-indexed
            rect = page.rect
            bbox = [rect.x0, rect.y0, rect.x1, rect.y1]

            # ------- Text extraction -------
            page_dict = page.get_text("dict")
            avg_font_size = _page_average_font_size(page_dict)
            full_text = _page_text_from_dict(page_dict)

            # ------- Scanned page detection -------
            is_scanned = len(full_text.strip()) < SCANNED_CHAR_THRESHOLD

            # ------- Section heading detection -------
            section_heading: str | None = None
            for block in page_dict.get("blocks", []):
                h = _detect_section_heading(block, avg_font_size)
                if h:
                    section_heading = h
                    break  # use the first (topmost) heading

            # ------- Table detection (PyMuPDF 1.23+) -------
            tables_md: list[str] = []
            try:
                found_tables = page.find_tables()
                for tbl in found_tables:
                    md = _blocks_to_markdown_table(tbl)
                    if md:
                        tables_md.append(md)
            except AttributeError:
                # Fallback: detect table-like blocks by bbox column alignment
                # (simplified heuristic — group text blocks into rows/cols)
                logger.debug("page.find_tables() not available; skipping table detection")

            # ------- Diagram detection -------
            has_images = len(page.get_images(full=True)) > 0
            drawing_count = len(page.get_drawings())
            has_diagram = has_images or drawing_count > DRAWING_DENSITY_THRESHOLD

            if has_diagram:
                diagram_pages.append(page_index)

            if is_scanned:
                scanned_pages.append(page_index)

            pages.append(
                {
                    "page_num": page_num,
                    "text": full_text,
                    "tables": tables_md,
                    "section_heading": section_heading,
                    "has_diagram": has_diagram,
                    "bbox": bbox,
                    "is_scanned": is_scanned,
                }
            )
    finally:
        doc.close()

    return {
        "pages": pages,
        "scanned_pages": scanned_pages,
        "diagram_pages": diagram_pages,
    }
