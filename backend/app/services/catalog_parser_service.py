from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation


@dataclass
class ParsedCatalogItem:
    product_code: str
    description: str | None = None
    technical_specification: str | None = None
    unit: str | None = None
    price: Decimal | None = None
    currency: str | None = "INR"
    page_number: int | None = None
    source_row_number: int | None = None


# ---------------------------------------------------------------------------
# PRODUCT CODE DETECTION
# ---------------------------------------------------------------------------

PRODUCT_CODE_PATTERNS = (
    # Examples:
    # 3WA1350-5AF32-0AA0
    # 3WA9111-0AD02
    # 3WT8061-6AA04-5AB2
    re.compile(
        r"^\d[A-Z]{2,4}\d{2,}[A-Z0-9/-]*$"
    ),

    # Examples:
    # 5SL61057RC
    # 5SL62057RC
    re.compile(
        r"^[A-Z]{2,6}\d{4,}[A-Z0-9]*$"
    ),
)


def normalize_text(value: str) -> str:
    return " ".join(
        value.replace("\u2003", " ").split()
    ).strip()


def looks_like_product_code(value: str) -> bool:
    text = normalize_text(value)

    if not text:
        return False

    if " " in text:
        return False

    if len(text) < 6:
        return False

    if re.fullmatch(r"[\d./,\-]+", text):
        return False

    return any(
        pattern.fullmatch(text)
        for pattern in PRODUCT_CODE_PATTERNS
    )


# ---------------------------------------------------------------------------
# PRICE DETECTION
# ---------------------------------------------------------------------------

def parse_price(value: str) -> Decimal | None:
    text = normalize_text(value)

    if not text:
        return None

    # Siemens uses values such as:
    #
    # 3887375.-
    # 610835.-
    #
    if text.endswith(".-"):
        text = text[:-2]

    text = (
        text
        .replace(",", "")
        .replace("₹", "")
        .replace("Rs.", "")
        .strip()
    )

    if not re.fullmatch(
        r"\d+(?:\.\d+)?",
        text,
    ):
        return None

    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def looks_like_price(value: str) -> bool:
    return parse_price(value) is not None


# ---------------------------------------------------------------------------
# SPECIAL VALUES
# ---------------------------------------------------------------------------

def is_por(value: str) -> bool:
    """
    Siemens price lists use POR for products whose price
    is not published in the extracted table.
    """

    return normalize_text(value).upper() == "POR"


def looks_like_placeholder(value: str) -> bool:
    return normalize_text(value) in {
        "–",
        "-",
        "—",
    }


# ---------------------------------------------------------------------------
# TECHNICAL SPECIFICATION DETECTION
# ---------------------------------------------------------------------------

def looks_like_voltage(value: str) -> bool:
    text = normalize_text(value)

    return bool(
        re.fullmatch(
            r"\d+(?:-\d+)?(?:\s*)?(?:V|VAC|V AC|V DC)",
            text,
            flags=re.IGNORECASE,
        )
    )


def looks_like_voltage_range(value: str) -> bool:
    text = normalize_text(value)

    return bool(
        re.fullmatch(
            r"\d+(?:-\d+)",
            text,
        )
    )


def looks_like_ratio(value: str) -> bool:
    text = normalize_text(value)

    return bool(
        re.fullmatch(
            r"\d+/\d+",
            text,
        )
    )


def looks_like_simple_number(value: str) -> bool:
    text = normalize_text(value)

    return bool(
        re.fullmatch(
            r"\d+(?:\.\d+)?",
            text,
        )
    )


def looks_like_technical_specification(value: str) -> bool:
    text = normalize_text(value)

    if not text:
        return False

    if looks_like_voltage(text):
        return True

    if looks_like_voltage_range(text):
        return True

    if looks_like_ratio(text):
        return True

    # Things such as:
    #
    # 2P
    # 415 V AC
    # 63
    #
    # are generally table attributes rather than descriptions.
    if re.fullmatch(
        r"\d+\s*[Pp]",
        text,
    ):
        return True

    if re.fullmatch(
        r"\d+(?:\.\d+)?\s*(?:A|kA|kW|Hz|mm|mm²)",
        text,
        flags=re.IGNORECASE,
    ):
        return True

    return False


# ---------------------------------------------------------------------------
# DESCRIPTION DETECTION
# ---------------------------------------------------------------------------

def looks_like_short_code_or_attribute(value: str) -> bool:
    text = normalize_text(value)

    if not text:
        return True

    if is_por(text):
        return True

    if looks_like_placeholder(text):
        return True

    if looks_like_product_code(text):
        return True

    if looks_like_price(text):
        return True

    if looks_like_technical_specification(text):
        return True

    return False


# ---------------------------------------------------------------------------
# MAIN PARSER
# ---------------------------------------------------------------------------

def parse_catalog_rows(rows) -> list[ParsedCatalogItem]:
    """
    Parse CatalogImportRow objects into preliminary catalog items.

    The PDF text extractor produces a vertical stream rather than
    preserving the original table columns.

    Therefore this parser uses:
        product code
        price
        POR
        technical-pattern detection

    to reconstruct the safest possible product records.

    We deliberately do NOT assign arbitrary numeric/attribute values
    as descriptions.
    """

    parsed: list[ParsedCatalogItem] = []

    current_item: ParsedCatalogItem | None = None

    ordered_rows = sorted(
        rows,
        key=lambda row: (
            row.page_number or 0,
            row.row_number or 0,
        ),
    )

    for row in ordered_rows:
        text = normalize_text(row.raw_text)

        if not text:
            continue

        # ---------------------------------------------------------------
        # PRODUCT CODE
        # ---------------------------------------------------------------

        if looks_like_product_code(text):

            current_item = ParsedCatalogItem(
                product_code=text,
                page_number=row.page_number,
                source_row_number=row.row_number,
            )

            parsed.append(current_item)

            continue

        # Everything below requires an active product.
        if current_item is None:
            continue

        # ---------------------------------------------------------------
        # PRICE
        # ---------------------------------------------------------------

        price = parse_price(text)

        if price is not None:

            if current_item.price is None:
                current_item.price = price

            continue

        # ---------------------------------------------------------------
        # PRICE = POR
        # ---------------------------------------------------------------

        if is_por(text):

            # We don't store POR in Decimal.
            #
            # The item remains valid with price=None.
            continue

        # ---------------------------------------------------------------
        # PLACEHOLDERS
        # ---------------------------------------------------------------

        if looks_like_placeholder(text):
            continue

        # ---------------------------------------------------------------
        # TECHNICAL SPECIFICATIONS
        # ---------------------------------------------------------------

        if looks_like_technical_specification(text):

            if current_item.technical_specification is None:

                current_item.technical_specification = text

            else:

                current_item.technical_specification += (
                    f"; {text}"
                )

            continue

        # ---------------------------------------------------------------
        # DESCRIPTION
        # ---------------------------------------------------------------

        # Only textual values should become descriptions.
        #
        # This prevents:
        #
        # 110-127
        # 1/12
        # 63
        # 415
        #
        # from becoming descriptions.

        if not looks_like_short_code_or_attribute(text):

            if current_item.description is None:

                current_item.description = text

            else:

                current_item.description += (
                    f" {text}"
                )


    return parsed


def parse_catalog_import_rows(rows) -> list[ParsedCatalogItem]:
    """
    Public parser entry point.
    """

    return parse_catalog_rows(rows)
import re

class CatalogParserService:
    def __init__(self):
        self.product_code_pattern = re.compile(r'^[A-Z0-9\-]{8,15}$')
        
    def parse_catalog_import_rows(self, rows):
        parsed_items = []
        current_item = None
        
        for row in rows:
            # 1. Check for boundaries (Headers, Page Footers)
            if self._is_table_header(row) or self._is_page_footer(row):
                continue
                
            # 2. Check for the Anchor (Product Code)
            potential_code = self._extract_product_code(row)
            
            if potential_code:
                # Flush the previous item if it exists
                if current_item:
                    parsed_items.append(self._finalize_item(current_item))
                    
                # Start a new buffer
                current_item = {
                    'product_code': potential_code,
                    'description_buffer': [self._extract_column(row, 'description')],
                    'technical_buffer': [self._extract_column(row, 'technical')],
                    'price': self._extract_column(row, 'price')
                }
            else:
                # 3. Append Phase (Multi-line text)
                if current_item:
                    desc_chunk = self._extract_column(row, 'description')
                    tech_chunk = self._extract_column(row, 'technical')
                    
                    if desc_chunk:
                        current_item['description_buffer'].append(desc_chunk)
                    if tech_chunk:
                        current_item['technical_buffer'].append(tech_chunk)

        # Flush the final item
        if current_item:
            parsed_items.append(self._finalize_item(current_item))
            
        return parsed_items

    def _finalize_item(self, item):
        # Join the buffered arrays with spaces to form the complete multi-line string
        return {
            'product_code': item['product_code'],
            'description': ' '.join(filter(None, item['description_buffer'])).strip(),
            'technical_specs': ' '.join(filter(None, item['technical_buffer'])).strip(),
            'price': item['price']
        }