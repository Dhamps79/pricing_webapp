import ipaddress
import json
import socket
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup


USER_AGENT = "LiveSpreadsheetPriceReader/0.1 (+local-development)"
TIMEOUT = httpx.Timeout(10.0, connect=5.0)


def _validate_target(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Only HTTP and HTTPS URLs are supported.")
    if not parsed.hostname:
        raise ValueError("The URL must contain a hostname.")

    # Development SSRF guard. For production, use an allowlist of trusted domains
    # and enforce DNS/IP checks at the network boundary as well.
    try:
        addresses = socket.getaddrinfo(parsed.hostname, None)
    except socket.gaierror as exc:
        raise ValueError("The source hostname could not be resolved.") from exc

    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise ValueError("Private or local network targets are not allowed.")


def _as_decimal(value) -> Decimal | None:
    if value is None:
        return None
    text = str(value).strip()
    text = text.replace(",", "")
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def _find_product_jsonld(soup: BeautifulSoup) -> dict | None:
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = script.string or script.get_text()
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            continue

        candidates = data if isinstance(data, list) else [data]
        if isinstance(data, dict) and isinstance(data.get("@graph"), list):
            candidates.extend(data["@graph"])

        for item in candidates:
            if not isinstance(item, dict):
                continue
            item_type = item.get("@type")
            types = item_type if isinstance(item_type, list) else [item_type]
            if "Product" in types:
                return item
    return None


async def lookup_price(url: str):
    _validate_target(url)

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml",
    }

    async with httpx.AsyncClient(
        timeout=TIMEOUT,
        follow_redirects=True,
        headers=headers,
    ) as client:
        response = await client.get(url)
        response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    product = _find_product_jsonld(soup)

    if not product:
        raise ValueError(
            "No Product JSON-LD was found. This source may require an official API "
            "or browser automation."
        )

    offers = product.get("offers")
    if isinstance(offers, list):
        offers = offers[0] if offers else {}
    offers = offers or {}

    image = product.get("image")
    if isinstance(image, list):
        image = image[0] if image else None

    return {
        "source_url": url,
        "product_name": product.get("name"),
        "price": _as_decimal(offers.get("price")),
        "currency": offers.get("priceCurrency"),
        "availability": offers.get("availability"),
        "image_url": image,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "source_type": "json-ld",
    }
