"""
docx_parser.py — Parse DOCX files by converting them to PDF via LibreOffice
                 (headless) and then delegating to pdf_parser.
"""
from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def convert_docx_to_pdf(docx_path: str, output_dir: str) -> str:
    """
    Convert a DOCX file to PDF using LibreOffice in headless mode.

    Parameters
    ----------
    docx_path : str
        Absolute or relative path to the input DOCX file.
    output_dir : str
        Directory where LibreOffice should write the output PDF.

    Returns
    -------
    str
        Absolute path to the generated PDF file.

    Raises
    ------
    RuntimeError
        If LibreOffice exits with a non-zero code or the expected PDF is not
        found after conversion.
    """
    docx_path_obj = Path(docx_path).resolve()
    output_dir_obj = Path(output_dir)
    output_dir_obj.mkdir(parents=True, exist_ok=True)

    cmd = [
        "libreoffice",
        "--headless",
        "--convert-to",
        "pdf",
        "--outdir",
        str(output_dir_obj),
        str(docx_path_obj),
    ]

    logger.info("Converting DOCX to PDF: %s", " ".join(cmd))
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(
            f"LibreOffice conversion timed out after 120 s for: {docx_path}"
        )

    if result.returncode != 0:
        raise RuntimeError(
            f"LibreOffice conversion failed (exit {result.returncode}).\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )

    # LibreOffice writes <stem>.pdf next to the outdir location
    expected_pdf = output_dir_obj / (docx_path_obj.stem + ".pdf")
    if not expected_pdf.exists():
        raise RuntimeError(
            f"LibreOffice conversion succeeded but expected PDF not found: {expected_pdf}"
        )

    logger.info("DOCX converted to PDF: %s", expected_pdf)
    return str(expected_pdf)


def parse_docx(
    file_path: str,
    doc_id: str,
    doc_name: str,
    work_dir: str,
) -> dict[str, Any]:
    """
    Parse a DOCX file and return structured page data.

    Steps:
    1. Convert the DOCX to PDF via LibreOffice.
    2. Parse the PDF with pdf_parser.parse_pdf().
    3. Open the original DOCX with python-docx and extract the heading
       hierarchy.
    4. Enrich each page_dict with the most relevant heading from the DOCX
       heading map (best-effort — DOCX paragraph order does not map 1:1 to
       PDF pages, so we match by position heuristic).

    Returns the same dict format as :func:`pdf_parser.parse_pdf`.
    """
    from app.services.ingestion import pdf_parser  # local import avoids circular

    # --- Step 1: convert to PDF ---
    pdf_path = convert_docx_to_pdf(file_path, work_dir)

    # --- Step 2: parse the PDF ---
    result = pdf_parser.parse_pdf(pdf_path, doc_id, doc_name)

    # --- Step 3: extract heading structure from original DOCX ---
    headings: list[str] = []
    try:
        import docx  # python-docx

        document = docx.Document(file_path)
        for para in document.paragraphs:
            style_name: str = para.style.name or ""
            if "heading" in style_name.lower() and para.text.strip():
                headings.append(para.text.strip())
    except Exception as exc:
        logger.warning("python-docx heading extraction failed: %s", exc)

    # --- Step 4: enrich page_dicts ---
    # Distribute headings evenly across pages (best-effort heuristic: assign
    # heading[i] to every page in the i-th equal-sized slice of the document).
    pages = result.get("pages", [])
    if headings and pages:
        pages_per_heading = max(1, len(pages) // len(headings))
        for idx, page_dict in enumerate(pages):
            heading_idx = min(idx // pages_per_heading, len(headings) - 1)
            # Only overwrite if the PDF parser did not already find a heading
            if not page_dict.get("section_heading"):
                page_dict["section_heading"] = headings[heading_idx]

    return result
