from dataclasses import dataclass
from pathlib import Path
from typing import Sequence, cast

import fitz  # PyMuPDF


@dataclass(frozen=True, slots=True)
class CoordinateWord:
    text: str

    x0: float
    y0: float
    x1: float
    y1: float

    block_no: int
    line_no: int
    word_no: int

    @property
    def x_center(self) -> float:
        return (self.x0 + self.x1) / 2

    @property
    def y_center(self) -> float:
        return (self.y0 + self.y1) / 2


@dataclass(frozen=True, slots=True)
class CoordinateRow:
    page_number: int
    y_center: float
    words: tuple[CoordinateWord, ...]

    @property
    def x0(self) -> float:
        return min(word.x0 for word in self.words)

    @property
    def x1(self) -> float:
        return max(word.x1 for word in self.words)

    @property
    def text(self) -> str:
        ordered_words = sorted(
            self.words,
            key=lambda word: word.x0,
        )

        return " ".join(
            word.text
            for word in ordered_words
        )


@dataclass(frozen=True, slots=True)
class Column:
    name: str
    x0: float
    x1: float


def _cluster_words_into_rows(
    words: list[CoordinateWord],
    *,
    page_number: int,
    y_tolerance: float = 2.0,
) -> list[CoordinateRow]:

    words = sorted(
        words,
        key=lambda word: (
            word.y_center,
            word.x0,
        ),
    )

    rows: list[dict] = []

    for word in words:
        target_row = None

        # Only inspect nearby rows because the words
        # are already sorted vertically.
        for row in reversed(rows[-4:]):
            if abs(
                word.y_center - row["y_center"]
            ) <= y_tolerance:
                target_row = row
                break

        if target_row is None:
            rows.append(
                {
                    "y_center": word.y_center,
                    "words": [word],
                }
            )
            continue

        target_row["words"].append(word)

        target_row["y_center"] = (
            sum(
                item.y_center
                for item in target_row["words"]
            )
            / len(target_row["words"])
        )

    return [
        CoordinateRow(
            page_number=page_number,
            y_center=row["y_center"],
            words=tuple(
                sorted(
                    row["words"],
                    key=lambda word: word.x0,
                )
            ),
        )
        for row in sorted(
            rows,
            key=lambda row: row["y_center"],
        )
    ]


def extract_pdf_coordinate_rows(
    file_path: str,
    page_numbers: Sequence[int] | None = None,
    *,
    y_tolerance: float = 2.0,
) -> dict[int, list[CoordinateRow]]:
    """
    Extract PDF text while preserving word coordinates.

    Unlike page.get_text("text"), this does not destroy
    the horizontal table structure.

    Returns:

        {
            page_number: [
                CoordinateRow(...),
                ...
            ]
        }

    Page numbers are 1-based.
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

    document = fitz.open(path)

    try:
        if page_numbers is None:
            selected_pages = range(
                1,
                len(document) + 1,
            )
        else:
            selected_pages = page_numbers

        result: dict[int, list[CoordinateRow]] = {}

        for page_number in selected_pages:
            if page_number < 1 or page_number > len(document):
                raise ValueError(
                    f"Invalid PDF page number: {page_number}"
                )

            page = document[
                page_number - 1
            ]

            words = cast(
                list[tuple[float, float, float, float, str, int, int, int]],
                page.get_text(
                    "words",
                    sort=False,
                ),
            )
            coordinate_words = [
                CoordinateWord(
                    text=word[4],
                    x0=word[0],
                    y0=word[1],
                    x1=word[2],
                    y1=word[3],
                    block_no=word[5],
                    line_no=word[6],
                    word_no=word[7],
                )
                for word in words
                if word[4].strip()
            ]

            result[page_number] = (
                _cluster_words_into_rows(
                    coordinate_words,
                    page_number=page_number,
                    y_tolerance=y_tolerance,
                )
            )

        return result

    finally:
        document.close()


def row_to_cells(
    row: CoordinateRow,
    columns: Sequence[Column],
) -> dict[str, str]:
    """
    Project coordinate words into named table columns.

    The extractor itself is layout-independent.

    Column definitions belong to the table parser because
    different PDF tables can have completely different
    column layouts.
    """

    cells: dict[str, list[str]] = {
        column.name: []
        for column in columns
    }

    for word in row.words:
        column = next(
            (
                column
                for column in columns
                if column.x0
                <= word.x_center
                < column.x1
            ),
            None,
        )

        if column is not None:
            cells[column.name].append(
                word.text
            )

    return {
        name: " ".join(values)
        for name, values in cells.items()
    }


# ------------------------------------------------------------------
# Existing extractor retained for backward compatibility
# ------------------------------------------------------------------

def extract_pdf_to_raw_rows(
    file_path: str,
) -> list[dict]:
    """
    Existing line-based extractor.

    Keep this temporarily for compatibility with the current
    CatalogImportRow pipeline.
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

    rows: list[dict] = []

    document = fitz.open(path)

    try:
        for page_index in range(len(document)):
            page = document[page_index]
            page_number = page_index + 1

            text = cast(str, page.get_text("text"))

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