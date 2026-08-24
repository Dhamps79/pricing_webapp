from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models.source import Source


def get_source_by_url(
    db: Session,
    url: str,
) -> Source | None:
    statement = select(Source).where(Source.url == url)
    return db.scalar(statement)


def create_source(
    db: Session,
    product_id: int,
    url: str,
    domain: str,
    source_type: str,
) -> Source:
    source = Source(
        product_id=product_id,
        url=url,
        domain=domain,
        source_type=source_type,
    )

    db.add(source)
    db.flush()

    return source