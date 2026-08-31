import re
from dataclasses import dataclass
from decimal import Decimal


PRODUCT_CODE_PATTERN = re.compile(
    r"^[A-Z0-9][A-Z0-9\-]{4,}$"
)


@dataclass
class ParsedCatalogProduct:
    product_code: str
    description: str | None = None
    price: Decimal | None = None
    unit: str | None = None
    standard_package: str | None = None
    category: str | None = None
    brand: str = "Siemens"

def looks_like_product_code(value: str) -> bool:
    value = value.strip()

    if not value:
        return False

    return bool(PRODUCT_CODE_PATTERN.match(value))

SIEMENS_CODE_PATTERN = re.compile(
    r"^(?:"
    r"5SL|"
    r"5SU|"
    r"5SV|"
    r"5SM|"
    r"5SP|"
    r"5ST|"
    r"5SD|"
    r"8GB|"
    r"7KN|"
    r"7LQ|"
    r"5TE|"
    r"5TL"
    r")[A-Z0-9\-]+$",
    re.IGNORECASE,
)


def is_siemens_product_code(value: str) -> bool:
    value = value.strip()

    return bool(
        SIEMENS_CODE_PATTERN.match(value)
    )

def extract_product_codes(
    text: str,
) -> list[str]:

    results: list[str] = []

    for line in text.splitlines():

        value = line.strip()

        if is_siemens_product_code(value):
            results.append(value)
            

    return results