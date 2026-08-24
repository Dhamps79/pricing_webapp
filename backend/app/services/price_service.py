import ipaddress
import json
import socket
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from datetime import datetime

from sqlalchemy.orm import Session

from app.repos.price_history_repo import (
    get_latest_price,
    get_price_history,
)
from app.repos.product_repo import get_product_by_id

from app.repos.product_repo import (
    create_product,
    get_product_by_name,
)
from app.repos.source_repo import (
    create_source,
    get_source_by_url,
)
from app.repos.price_history_repo import (
    create_price_history,
)
USER_AGENT = "LiveSpreadsheetPriceReader/0.1 (+local-development)"
TIMEOUT = httpx.Timeout(10.0, connect=5.0)
async def track_price(
    db: Session,
    url: str,
):
    data = await lookup_price(url)

    try:
        # 1. Find or create Product
        product = get_product_by_name(
            db,
            data["product_name"],
        )

        if product is None:
            product = create_product(
                db=db,
                name=data["product_name"],
                image_url=data["image_url"],
            )

        # 2. Find or create Source
        source = get_source_by_url(
            db,
            data["source_url"],
        )

        if source is None:
            parsed = urlparse(data["source_url"])

            source = create_source(
                db=db,
                product_id=product.id,
                url=data["source_url"],
                domain=parsed.hostname or "",
                source_type=data["source_type"],
            )

        # 3. Create price history record
        fetched_at = datetime.fromisoformat(
            data["fetched_at"]
        )

        history = create_price_history(
            db=db,
            product_id=product.id,
            source_id=source.id,
            price=data["price"],
            currency=data["currency"],
            availability=data["availability"],
            fetched_at=fetched_at,
        )

        # 4. Commit everything as one transaction
        db.commit()

        # Refresh objects from PostgreSQL
        db.refresh(product)
        db.refresh(source)
        db.refresh(history)

        return {
            "product": product,
            "source": source,
            "price_history": history,
        }

    except Exception:
        db.rollback()
        raise

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

def get_current_price(
    db: Session,
    product_id: int,
):
    product = get_product_by_id(
        db,
        product_id,
    )

    if product is None:
        return None

    latest = get_latest_price(
        db,
        product_id,
    )

    if latest is None:
        return None

    return {
        "product": product,
        "price": latest,
    }

def get_product_price_history(
    db: Session,
    product_id: int,
):
    product = get_product_by_id(
        db,
        product_id,
    )

    if product is None:
        return None

    history = get_price_history(
        db,
        product_id,
    )

    return {
        "product": product,
        "history": history,
    }