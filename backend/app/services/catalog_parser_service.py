from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation


PRODUCT_CODE_PATTERNS = (
    # Siemens codes such as:
    # 3WA1350-5AF32-0AA0
    # 3WA9111-0AD02
    # 3WT8061-6AA04-5AB2
    re.compile(r"^\d[A-Z]{2,4}\d{2,}[A-Z0-9/-]*$", re.IGNORECASE),

    # Siemens codes such as:
    # 5SL71057RC
    # 5SL62057RC
    re.compile(r"^[A-Z]{2,6}\d{4,}[A-Z0-9]*$", re.IGNORECASE),
)


def normalize_text(value: str | None) -> str:
    if not value:
        return ""

    return " ".join(
        value.replace("\u2003", " ").split()
    ).strip()


def normalize_product_code(value: str | None) -> str | None:
    value = normalize_text(value)

    if not value:
        return None

    value = value.upper()

    if not looks_like_product_code(value):
        return None

    return value


def looks_like_product_code(value: str | None) -> bool:
    value = normalize_text(value)

    if not value:
        return False

    if " " in value:
        return False

    if len(value) < 6:
        return False

    if re.fullmatch(r"[\d./,\-]+", value):
        return False

    return any(
        pattern.fullmatch(value)
        for pattern in PRODUCT_CODE_PATTERNS
    )


def parse_price(value: str | None) -> Decimal | None:
    value = normalize_text(value)

    if not value:
        return None

    # Siemens notation:
    # 925.-
    # 5595.-
    if value.endswith(".-"):
        value = value[:-2]

    value = (
        value
        .replace(",", "")
        .replace("₹", "")
        .replace("Rs.", "")
        .strip()
    )

    if not re.fullmatch(r"\d+(?:\.\d+)?", value):
        return None

    try:
        return Decimal(value)
    except InvalidOperation:
        return None


def is_por(value: str | None) -> bool:
    return normalize_text(value).upper() == "POR"


def is_placeholder(value: str | None) -> bool:
    return normalize_text(value) in {
        "-",
        "–",
        "—",
    }


def looks_like_numeric_attribute(value: str | None) -> bool:
    value = normalize_text(value)

    if not value:
        return False

    patterns = (
        r"\d+(?:\.\d+)?",
        r"\d+(?:\.\d+)?\s*[Pp]",
        r"\d+(?:\.\d+)?\s*(?:A|kA|kW|Hz|mm|mm²)",
        r"\d+(?:-\d+)",
        r"\d+/\d+",
    )

    return any(
        re.fullmatch(
            pattern,
            value,
            flags=re.IGNORECASE,
        )
        for pattern in patterns
    )


def normalize_description(value: str | None) -> str | None:
    value = normalize_text(value)

    if not value:
        return None

    if looks_like_product_code(value):
        return None

    if parse_price(value) is not None:
        return None

    if is_por(value):
        return None

    if is_placeholder(value):
        return None

    if looks_like_numeric_attribute(value):
        return None

    return value