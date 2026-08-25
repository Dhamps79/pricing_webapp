from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import pdfplumber

PRICE_RE = re.compile(r"(?P<price>\d{1,3}(?:,\d{3})+|\d+)\.-")
SKU_RE = re.compile(r"\b(?P<sku>\d[A-Z0-9][A-Z0-9.\-]{3,40}[A-Z0-9])\b")
PACK_RE = re.compile(r"(\d+/\d+|\d+)\s*$")
GROUP_RE = re.compile(
    r"^(\d+\s*P\b|.*\b(AC|DC|V AC|V DC)\b|.*\b(contactor|relay|MCCB|MCB|RCCB)\b)",
    re.IGNORECASE,
)
SKIP_FAMILY = (
    "price list",
    "siemens limited",
    "siemens.com",
    "index",
    "contents",
    "note:",
    "www.",
)


@dataclass(frozen=True)
class ParsedCatalogItem:
    sku: str
    name: str
    description: str
    category: str
    unit: str | None
    list_price: float
    page: int
    source_file: str
    source_title: str


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip(" -|")


def _is_family_line(line: str) -> bool:
    lowered = line.lower()
    if any(token in lowered for token in SKIP_FAMILY):
        return False
    if PRICE_RE.search(line) or SKU_RE.search(line):
        return False
    if len(line) < 8 or len(line) > 90:
        return False
    return bool(re.search(r"[A-Za-z]", line))


def _pairs_from_line(line: str) -> list[tuple[str, float, str | None]]:
    skus = list(SKU_RE.finditer(line))
    prices = list(PRICE_RE.finditer(line))
    if not skus or not prices:
        return []

    pairs: list[tuple[str, float, str | None]] = []
    used_prices: set[int] = set()

    for sku_match in skus:
        sku = sku_match.group("sku")
        if not re.search(r"[A-Za-z]", sku):
            continue

        chosen = None
        for index, price_match in enumerate(prices):
            if index in used_prices:
                continue
            if price_match.start() >= sku_match.end():
                chosen = (index, price_match)
                break

        if chosen is None:
            continue

        used_prices.add(chosen[0])
        price = float(chosen[1].group("price").replace(",", ""))
        after = line[chosen[1].end() :]
        pack_match = PACK_RE.search(after.strip())
        unit = pack_match.group(1) if pack_match else None
        pairs.append((sku, price, unit))

    return pairs


def parse_pricelist_pdf(
    pdf_path: str | Path,
    source_title: str,
) -> list[ParsedCatalogItem]:
    path = Path(pdf_path)
    items: dict[str, ParsedCatalogItem] = {}
    family = source_title
    group = ""

    with pdfplumber.open(path) as pdf:
        for page_index, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            lines = [_clean(line) for line in text.splitlines() if _clean(line)]

            for line in lines[:12]:
                if _is_family_line(line):
                    family = line
                    break

            for line in lines:
                if GROUP_RE.search(line) and not PRICE_RE.search(line) and len(line) < 90:
                    group = line

                pairs = _pairs_from_line(line)
                if not pairs:
                    continue

                prefix = SKU_RE.split(line)[0]
                rating = _clean(prefix)
                for sku, price, unit in pairs:
                    parts = [family]
                    if group:
                        parts.append(group)
                    if rating and rating not in group:
                        parts.append(rating)
                    description = " | ".join(part for part in parts if part)
                    name = f"{sku} — {description}"[:500]
                    items[sku] = ParsedCatalogItem(
                        sku=sku,
                        name=name,
                        description=description[:4000],
                        category=family[:255],
                        unit=unit,
                        list_price=price,
                        page=page_index + 1,
                        source_file=path.name,
                        source_title=source_title,
                    )

    return list(items.values())
