from pathlib import Path

import fitz  # PyMuPDF


def extract_pdf_to_raw_rows(file_path: str) -> list[dict]:
    """
    Extract text from a PDF and return one raw row per
    non-empty line.

    Each returned item contains:
        page_number
        row_number
        raw_text
    """

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"PDF file not found: {path}")

    if path.suffix.lower() != ".pdf":
        raise ValueError("Only PDF files are supported.")

    rows: list[dict] = []

    document = fitz.open(path)

    try:
        for page_index, page in enumerate(document):
            page_number = page_index + 1

            text = page.get_text("text")

            if not text:
                continue

            row_number = 0

            for line in text.splitlines():
                raw_text = line.strip()

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