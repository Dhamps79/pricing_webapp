from pathlib import Path

from pypdf import PdfReader


def extract_pdf_to_raw_rows(
    file_path: str | Path,
) -> list[dict]:
    """
    Extract text from every page of a PDF.

    Each page becomes a raw catalog row.

    We deliberately do NOT try to interpret product names,
    codes, prices, etc. at this stage.

    PDF parsing and product normalization are separate stages.
    """

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(
            f"PDF file not found: {path}"
        )

    if path.suffix.lower() != ".pdf":
        raise ValueError(
            "Only PDF files are supported."
        )

    reader = PdfReader(str(path))

    raw_rows: list[dict] = []

    for page_number, page in enumerate(
        reader.pages,
        start=1,
    ):
        text = page.extract_text() or ""

        text = text.strip()

        if not text:
            continue

        raw_rows.append(
            {
                "page_number": page_number,
                "row_number": len(raw_rows) + 1,
                "raw_text": text,
                "parsed_status": "pending",
            }
        )

    return raw_rows