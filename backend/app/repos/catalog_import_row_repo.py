from sqlalchemy.orm import Session

from app.database.models.catalog_import_row import CatalogImportRow


def create_raw_row(
    db: Session,
    *,
    import_id: int,
    page_number: int,
    row_number: int,
    raw_text: str,
) -> CatalogImportRow:

    row = CatalogImportRow(
        import_id=import_id,
        page_number=page_number,
        row_number=row_number,
        raw_text=raw_text,
        parsed_status="pending",
    )

    db.add(row)
    db.flush()

    return row

def create_raw_rows(
    db: Session,
    *,
    import_id: int,
    page_number: int,
    lines: list[str],
) -> list[CatalogImportRow]:

    rows: list[CatalogImportRow] = []

    for index, line in enumerate(lines, start=1):

        cleaned = line.strip()

        if not cleaned:
            continue

        row = CatalogImportRow(
            import_id=import_id,
            page_number=page_number,
            row_number=index,
            raw_text=cleaned,
            parsed_status="pending",
        )

        db.add(row)
        rows.append(row)

    db.flush()

    return rows