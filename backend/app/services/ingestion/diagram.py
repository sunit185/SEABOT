"""
diagram.py — Diagram detection, page rendering, thumbnail saving, and
             async Ollama vision captioning.
"""
from __future__ import annotations

import base64
import io
import json
import logging
import os
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def render_page_png(pdf_path: str, page_num: int, dpi: int = 150) -> bytes:
    """
    Render a PDF page as PNG bytes.

    Parameters
    ----------
    pdf_path : str
        Path to the PDF file.
    page_num : int
        0-indexed page number.
    dpi : int
        Rendering resolution.

    Returns
    -------
    bytes
        Raw PNG bytes.
    """
    import fitz  # PyMuPDF

    doc = fitz.open(pdf_path)
    try:
        page = doc[page_num]
        zoom = dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)
        pixmap = page.get_pixmap(matrix=mat, alpha=False)
        return pixmap.tobytes("png")
    finally:
        doc.close()


def save_thumbnail(
    png_bytes: bytes,
    doc_id: str,
    page_num: int,
    thumbnails_dir: str,
) -> str:
    """
    Persist a rendered page PNG as a thumbnail.

    Parameters
    ----------
    png_bytes : bytes
        Raw PNG bytes from :func:`render_page_png`.
    doc_id : str
        Document UUID (used as subdirectory name).
    page_num : int
        0-indexed page number (stored as 1-indexed filename).
    thumbnails_dir : str
        Root thumbnails directory (e.g. ``./data/thumbnails``).

    Returns
    -------
    str
        Absolute path to the saved thumbnail file.
    """
    dest_dir = Path(thumbnails_dir) / doc_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    # Store as 1-indexed, zero-padded for filesystem sorting
    filename = f"page_{(page_num + 1):04d}.png"
    dest_path = dest_dir / filename
    dest_path.write_bytes(png_bytes)
    return str(dest_path)


async def caption_diagram(
    png_bytes: bytes,
    ollama_client: Any,
    model: str,
) -> dict[str, Any]:
    """
    Use an Ollama vision model to caption a diagram page.

    Sends the image (base64-encoded) together with Prompt B to the Ollama
    ``generate`` endpoint and parses the JSON response.

    Parameters
    ----------
    png_bytes : bytes
        Raw PNG bytes of the page to caption.
    ollama_client : OllamaClient
        Instantiated Ollama HTTP client (see services/llm/ollama_client.py).
    model : str
        Vision-capable model name (e.g. ``gemma4:12b``).

    Returns
    -------
    dict
        Parsed JSON dict from model output, or ``{}`` on any parse failure.
    """
    from app.services.llm.prompts import PROMPT_B  # local import to avoid circular deps

    image_b64 = base64.b64encode(png_bytes).decode("utf-8")

    try:
        raw_response: str = await ollama_client.generate(
            model=model,
            prompt=PROMPT_B,
            images=[image_b64],
        )
    except Exception as exc:
        logger.error("caption_diagram: ollama generate failed: %s", exc)
        return {}

    # Strip optional markdown code fences
    cleaned = raw_response.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        logger.warning("caption_diagram: JSON parse failed (%s). Raw: %s", exc, raw_response[:200])
        return {}


def is_diagram_page(fitz_page: Any) -> bool:
    """
    Return True if the page likely contains a diagram.

    Criteria (either condition triggers):
    - The page has at least one embedded image.
    - The page has more than 20 vector drawing operations.
    """
    has_images = len(fitz_page.get_images(full=True)) > 0
    has_many_drawings = len(fitz_page.get_drawings()) > 20
    return has_images or has_many_drawings
