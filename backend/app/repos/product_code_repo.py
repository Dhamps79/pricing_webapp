from sqlalchemy.orm import Session

from app.database.models.product_code import ProductCode


def get_product_code_by_id(
    db: Session,
    code_id: int,
) -> ProductCode | None:
    return (
        db.query(ProductCode)
        .filter(ProductCode.id == code_id)
        .first()
    )


def get_product_code(
    db: Session,
    code: str,
    code_type: str | None = None,
) -> ProductCode | None:
    query = (
        db.query(ProductCode)
        .filter(ProductCode.code == code)
    )

    if code_type is not None:
        query = query.filter(
            ProductCode.code_type == code_type
        )

    return query.first()


def get_product_codes_for_product(
    db: Session,
    product_id: int,
) -> list[ProductCode]:
    return (
        db.query(ProductCode)
        .filter(ProductCode.product_id == product_id)
        .order_by(
            ProductCode.is_primary.desc(),
            ProductCode.id.asc(),
        )
        .all()
    )


def get_primary_product_code(
    db: Session,
    product_id: int,
) -> ProductCode | None:
    return (
        db.query(ProductCode)
        .filter(
            ProductCode.product_id == product_id,
            ProductCode.is_primary.is_(True),
        )
        .first()
    )


def search_product_codes(
    db: Session,
    code: str,
    *,
    code_type: str | None = None,
    limit: int = 20,
) -> list[ProductCode]:

    query = (
        db.query(ProductCode)
        .filter(
            ProductCode.code.ilike(
                f"%{code.strip()}%"
            )
        )
    )

    if code_type is not None:
        query = query.filter(
            ProductCode.code_type == code_type
        )

    return (
        query
        .order_by(
            ProductCode.is_primary.desc(),
            ProductCode.code.asc(),
        )
        .limit(limit)
        .all()
    )


def create_product_code(
    db: Session,
    *,
    product_id: int,
    code: str,
    code_type: str,
    is_primary: bool = False,
) -> ProductCode:

    product_code = ProductCode(
        product_id=product_id,
        code=code.strip(),
        code_type=code_type,
        is_primary=is_primary,
    )

    db.add(product_code)
    db.flush()

    return product_code


def delete_product_code(
    db: Session,
    product_code: ProductCode,
) -> None:
    db.delete(product_code)
    db.flush()