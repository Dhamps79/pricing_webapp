from pathlib import Path

import pymupdf


def extract_pdf_to_raw_rows(file_path: str | Path) -> list[dict]:
    """
    Extract text from every page of a PDF.

    Returns one raw row per extracted text block.

    The purpose of this function is intentionally limited:
    PDF -> raw text.

    It does NOT try to understand Siemens product fields yet.
    Structured parsing will happen in the next layer.
    """

    pdf_path = Path(file_path)

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError("Only PDF files are supported")

    rows: list[dict] = []

    document = fitz.open(pdf_path)

    try:
        for page_index, page in enumerate(document):
            page_number = page_index + 1

            blocks = page.get_text("blocks")

            row_number = 0

            for block in blocks:
                if len(block) < 5:
                    continue

                raw_text = block[4].strip()

                if not raw_text:
                    continue

                row_number += 1

                rows.append(
                    {
                        "page_number": page_number,
                        "row_number": row_number,
                        "raw_text": raw_text,
                    }
                )

    finally:
        document.close()

    return rows

