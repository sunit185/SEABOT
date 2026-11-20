"""
excel_parser.py — Parse Excel files (.xlsx) using openpyxl.

Each worksheet is converted to a series of markdown-table chunk dicts with
up to 20 data rows per chunk (header is repeated at the top of each chunk).
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

logger = logging.getLogger(__name__)

ROWS_PER_CHUNK = 20


def _resolve_merged(sheet: Any) -> dict[tuple[int, int], Any]:
    """
    Build a mapping (row, col) -> cell_value that expands merged cell ranges.

    openpyxl reports only the top-left cell of a merged range; all other cells
    inside the range have a MergedCell proxy with no value.  This helper maps
    every coordinate within a merged range to the top-left cell's value so
    callers can read any cell uniformly.
    """
    merged_values: dict[tuple[int, int], Any] = {}
    for merged_range in sheet.merged_cells.ranges:
        top_left_cell = sheet.cell(row=merged_range.min_row, column=merged_range.min_col)
        value = top_left_cell.value
        for row in range(merged_range.min_row, merged_range.max_row + 1):
            for col in range(merged_range.min_col, merged_range.max_col + 1):
                merged_values[(row, col)] = value
    return merged_values


def _get_cell_value(
    sheet: Any,
    row: int,
    col: int,
    merged_map: dict[tuple[int, int], Any],
) -> str:
    """Return the string representation of a cell, respecting merged ranges."""
    if (row, col) in merged_map:
        val = merged_map[(row, col)]
    else:
        val = sheet.cell(row=row, column=col).value
    if val is None:
        return ""
    return str(val)


def _rows_to_markdown(
    sheet: Any,
    header_row: int,
    data_rows: list[int],
    num_cols: int,
    merged_map: dict[tuple[int, int], Any],
) -> str:
    """Format a header row + a slice of data rows as a Markdown table."""
    header_cells = [
        _get_cell_value(sheet, header_row, col, merged_map)
        for col in range(1, num_cols + 1)
    ]
    lines: list[str] = []
    lines.append("| " + " | ".join(header_cells) + " |")
    lines.append("| " + " | ".join(["---"] * num_cols) + " |")
    for row_idx in data_rows:
        cells = [
            _get_cell_value(sheet, row_idx, col, merged_map)
            for col in range(1, num_cols + 1)
        ]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def parse_excel(file_path: str, doc_id: str, doc_name: str) -> list[dict[str, Any]]:
    """
    Parse an Excel workbook and return a flat list of chunk dicts.

    Each chunk represents up to ``ROWS_PER_CHUNK`` rows of one worksheet,
    formatted as a Markdown table with the header repeated at the top.

    Chunk dict keys:
        chunk_id, doc_id, doc_name, page, section_heading, chunk_type,
        text, sheet_name, row_range, bbox
    """
    import openpyxl

    wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
    result: list[dict[str, Any]] = []

    for sheet in wb.worksheets:
        # Collect all non-completely-empty rows
        all_rows = list(sheet.iter_rows(values_only=False))
        if not all_rows:
            continue

        # Find the first non-empty row (header)
        header_row_index: int | None = None
        for i, row in enumerate(all_rows):
            if any(cell.value is not None for cell in row):
                header_row_index = i
                break

        if header_row_index is None:
            logger.debug("Skipping empty sheet: %s", sheet.title)
            continue

        # Determine number of columns from header row
        header_row_cells = all_rows[header_row_index]
        num_cols = len(header_row_cells)
        if num_cols == 0:
            continue

        # NOTE: read_only workbooks do not support merged_cells; we guard here.
        try:
            wb_full = openpyxl.load_workbook(file_path, read_only=False, data_only=True)
            sheet_full = wb_full[sheet.title]
            merged_map = _resolve_merged(sheet_full)
        except Exception:
            merged_map = {}
            sheet_full = sheet  # type: ignore[assignment]

        # openpyxl sheet.min_row is 1-indexed; header row number in sheet coords
        sheet_header_row = sheet.min_row + header_row_index

        # Collect data rows (everything after the header)
        data_row_indices = list(
            range(sheet_header_row + 1, sheet.max_row + 1)
        )

        if not data_row_indices:
            # Only a header, nothing to chunk
            continue

        # Chunk data rows into groups of ROWS_PER_CHUNK
        for chunk_start_pos in range(0, len(data_row_indices), ROWS_PER_CHUNK):
            chunk_data_rows = data_row_indices[
                chunk_start_pos: chunk_start_pos + ROWS_PER_CHUNK
            ]
            markdown_table = _rows_to_markdown(
                sheet_full,
                header_row=sheet_header_row,
                data_rows=chunk_data_rows,
                num_cols=num_cols,
                merged_map=merged_map,
            )

            if not markdown_table.strip():
                continue

            row_range_start = chunk_data_rows[0]
            row_range_end = chunk_data_rows[-1]

            result.append(
                {
                    "chunk_id": str(uuid.uuid4()),
                    "doc_id": doc_id,
                    "doc_name": doc_name,
                    "page": 1,
                    "section_heading": sheet.title,
                    "chunk_type": "sheet_rows",
                    "text": markdown_table,
                    "sheet_name": sheet.title,
                    "row_range": [row_range_start, row_range_end],
                    "bbox": None,
                }
            )

    wb.close()
    return result
