from app.database.schema import ensure_schema
from app.database.sessions import SessionLocal
from app.services.catalog_import_service import import_pricelists


def main() -> None:
    ensure_schema()
    db = SessionLocal()
    try:
        result = import_pricelists(db)
        print(result)
    finally:
        db.close()


if __name__ == "__main__":
    main()
