from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from app.services.catalog_parser_service import (
    normalize_product_code,
    normalize_text,
    parse_price,
)
from app.services.pdf_service import (
    Column,
    CoordinateRow,
    extract_pdf_coordinate_rows,
    row_to_cells,
)


# ---------------------------------------------------------------------------
# Parsed domain object
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ParsedCatalogProduct:
    """
    Normalized representation of one product extracted from a supplier
    catalog.

    This object is deliberately independent of SQLAlchemy.
    The import service is responsible for persistence.
    """

    product_code: str
    description: str | None
    price: Decimal | None
    unit: str | None
    standard_package: str | None
    category: str | None
    brand: str = "Siemens"

    page_number: int | None = None
    source_row_number: int | None = None

    # Additional structured attributes extracted from the PDF.
    attributes: tuple[tuple[str, str], ...] = ()


# ---------------------------------------------------------------------------
# Siemens table definitions
# ---------------------------------------------------------------------------

# Verified against the supplied Siemens pricelist PDF.
#
# Pages 8 and 9 contain the 5SL7 MCB tables.
MCB_COLUMNS = (
    Column("section", 40, 245),
    Column("rated_current", 245, 310),
    Column("mw", 310, 350),
    Column("reference_no", 350, 435),
    Column("mrp", 435, 495),
    Column("standard_package", 495, 560),
)


# Verified against page 49 of the supplied PDF.
#
# DOL starter table:
#
# Motor Rating HP / kW
# Starter Type
# Contactor
# Thermal Overload Relay
# Relay Range
# Max Full Load Current
# MRP
# Std. Pkg.
DOL_COLUMNS = (
    Column("hp", 90, 125),
    Column("kw", 125, 155),
    Column("starter", 155, 220),
    Column("contactor", 220, 310),
    Column("overload_relay", 310, 365),
    Column("relay_range", 365, 400),
    Column("max_full_load_current", 400, 460),
    Column("mrp", 460, 515),
    Column("standard_package", 515, 550),
)


# ---------------------------------------------------------------------------
# Product-code handling
# ---------------------------------------------------------------------------


# Siemens reference numbers found in the supplied catalog include examples
# such as:
#
# 5SL71057RC
# 5SL74637RC
# 3TW7291-1A^64
# 3TS3010-0A##-08KA0
# 3UW5102-0J
#
# The parser must therefore tolerate:
# - letters
# - digits
# - hyphens
# - slash
# - caret
# - hash placeholders
#
SIEMENS_REFERENCE_PATTERN = re.compile(
    r"^[A-Z0-9][A-Z0-9\-/^#]{5,}$",
    re.IGNORECASE,
)


def is_siemens_reference(value: str | None) -> bool:
    value = normalize_text(value)

    if not value:
        return False

    if " " in value:
        return False

    return bool(
        SIEMENS_REFERENCE_PATTERN.fullmatch(value)
    )


def normalize_siemens_reference(
    value: str | None,
) -> str | None:
    value = normalize_text(value)

    if not value:
        return None

    value = value.upper()

    if not is_siemens_reference(value):
        return None

    return normalize_product_code(value) or value


# ---------------------------------------------------------------------------
# General row helpers
# ---------------------------------------------------------------------------


def _clean_cell(
    cells: dict[str, str],
    key: str,
) -> str | None:
    value = normalize_text(cells.get(key))
    return value or None


def _parse_optional_decimal(
    value: str | None,
) -> Decimal | None:
    return parse_price(value)


def _attribute_tuple(
    *items: tuple[str, str | None],
) -> tuple[tuple[str, str], ...]:
    return tuple(
        (name, value)
        for name, value in items
        if value
    )


def _deduplicate_products(
    products: Iterable[ParsedCatalogProduct],
) -> list[ParsedCatalogProduct]:
    """
    Deduplicate by manufacturer reference number.

    The same reference can occasionally appear more than once when a PDF
    contains repeated table headers or continuation sections.
    """

    seen: set[str] = set()
    result: list[ParsedCatalogProduct] = []

    for product in products:
        if product.product_code in seen:
            continue

        seen.add(product.product_code)
        result.append(product)

    return result


# ---------------------------------------------------------------------------
# MCB parser
# ---------------------------------------------------------------------------


def parse_mcb_rows(
    rows: Iterable[CoordinateRow],
    *,
    category: str = "Miniature Circuit Breakers",
) -> list[ParsedCatalogProduct]:
    """
    Parse Siemens 5SL7 MCB table rows.

    The table is the layout verified on pages 8 and 9 of the supplied
    Siemens pricelist.
    """

    products: list[ParsedCatalogProduct] = []

    for row in rows:
        cells = row_to_cells(
            row,
            MCB_COLUMNS,
        )

        reference_no = normalize_siemens_reference(
            cells.get("reference_no")
        )

        if not reference_no:
            continue

        rated_current = _clean_cell(
            cells,
            "rated_current",
        )

        mw = _clean_cell(
            cells,
            "mw",
        )

        section = _clean_cell(
            cells,
            "section",
        )

        standard_package = _clean_cell(
            cells,
            "standard_package",
        )

        price = _parse_optional_decimal(
            cells.get("mrp")
        )

        description_parts = [
            "Siemens 5SL7 Miniature Circuit Breaker",
        ]

        if section:
            description_parts.append(section)

        if rated_current:
            description_parts.append(
                f"{rated_current} A"
            )

        description = " - ".join(
            description_parts
        )

        attributes = _attribute_tuple(
            ("rated_current", rated_current),
            ("module_width", mw),
            ("section", section),
        )

        products.append(
            ParsedCatalogProduct(
                product_code=reference_no,
                description=description,
                price=price,
                unit="Nos",
                standard_package=standard_package,
                category=category,
                brand="Siemens",
                page_number=row.page_number,
                attributes=attributes,
            )
        )

    return _deduplicate_products(products)


# ---------------------------------------------------------------------------
# DOL starter parser
# ---------------------------------------------------------------------------


def _looks_like_dol_starter_code(
    value: str | None,
) -> bool:
    value = normalize_text(value)

    if not value:
        return False

    return bool(
        re.fullmatch(
            r"3TW[A-Z0-9\-/^#]+",
            value,
            flags=re.IGNORECASE,
        )
    )


def parse_dol_rows(
    rows: Iterable[CoordinateRow],
    *,
    category: str = "DOL Starters",
) -> list[ParsedCatalogProduct]:
    """
    Parse Siemens DOL starter rows.

    Layout verified against page 49 of the supplied catalog.
    """

    products: list[ParsedCatalogProduct] = []

    for row in rows:
        cells = row_to_cells(
            row,
            DOL_COLUMNS,
        )

        starter_code = normalize_text(
            cells.get("starter")
        )

        if not _looks_like_dol_starter_code(
            starter_code
        ):
            continue

        starter_code = starter_code.upper()

        hp = _clean_cell(
            cells,
            "hp",
        )

        kw = _clean_cell(
            cells,
            "kw",
        )

        contactor = _clean_cell(
            cells,
            "contactor",
        )

        overload_relay = _clean_cell(
            cells,
            "overload_relay",
        )

        relay_range = _clean_cell(
            cells,
            "relay_range",
        )

        max_full_load_current = _clean_cell(
            cells,
            "max_full_load_current",
        )

        standard_package = _clean_cell(
            cells,
            "standard_package",
        )

        price = _parse_optional_decimal(
            cells.get("mrp")
        )

        description_parts = [
            "Siemens DOL Starter",
        ]

        if hp:
            description_parts.append(
                f"{hp} HP"
            )

        if kw:
            description_parts.append(
                f"{kw} kW"
            )

        description = " - ".join(
            description_parts
        )

        attributes = _attribute_tuple(
            ("motor_rating_hp", hp),
            ("motor_rating_kw", kw),
            ("contactor", contactor),
            ("thermal_overload_relay", overload_relay),
            ("relay_range", relay_range),
            (
                "max_full_load_current",
                max_full_load_current,
            ),
        )

        products.append(
            ParsedCatalogProduct(
                product_code=starter_code,
                description=description,
                price=price,
                unit="Nos",
                standard_package=standard_package,
                category=category,
                brand="Siemens",
                page_number=row.page_number,
                attributes=attributes,
            )
        )

    return _deduplicate_products(products)


# ---------------------------------------------------------------------------
# Page/table detection
# ---------------------------------------------------------------------------


def _page_text(
    rows: Iterable[CoordinateRow],
) -> str:
    return " ".join(
        row.text
        for row in rows
    ).lower()


def detect_table_type(
    page_number: int,
    rows: list[CoordinateRow],
) -> str | None:
    """
    Identify supported Siemens table layouts.

    Page numbers are used as a guard because coordinates are meaningful only
    for the corresponding table layout. Header/text checks provide an
    additional safety mechanism.
    """

    text = _page_text(rows)

    # Verified 5SL7 MCB pages.
    if page_number in {8, 9}:
        if (
            "reference" in text
            and "mrp" in text
        ):
            return "mcb"

    # Verified DOL starter page.
    if page_number == 49:
        if (
            "starter" in text
            and "contactor" in text
            and "thermal" in text
        ):
            return "dol"

    return None


# ---------------------------------------------------------------------------
# Page parsing
# ---------------------------------------------------------------------------


def parse_page(
    page_number: int,
    rows: list[CoordinateRow],
) -> list[ParsedCatalogProduct]:
    table_type = detect_table_type(
        page_number,
        rows,
    )

    if table_type == "mcb":
        return parse_mcb_rows(rows)

    if table_type == "dol":
        return parse_dol_rows(rows)

    return []


# ---------------------------------------------------------------------------
# Complete document parser
# ---------------------------------------------------------------------------


def parse_siemens_pdf(
    file_path: str,
    *,
    page_numbers: list[int] | None = None,
) -> list[ParsedCatalogProduct]:
    """
    Parse all currently supported Siemens tables from a PDF.

    Unsupported pages are deliberately skipped.

    This is important for production: the importer must never manufacture
    products from a table layout it does not understand.
    """

    pages = extract_pdf_coordinate_rows(
        file_path,
        page_numbers=page_numbers,
    )

    products: list[ParsedCatalogProduct] = []

    for page_number in sorted(pages):
        products.extend(
            parse_page(
                page_number,
                pages[page_number],
            )
        )

    return _deduplicate_products(products)