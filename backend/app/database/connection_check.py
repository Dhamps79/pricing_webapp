from sqlalchemy import text

from app.database.engine import engine


def main() -> None:
    with engine.connect() as connection:
        result = connection.execute(
            text("SELECT 1")
        )

        print(
            "Database connection successful:",
            result.scalar(),
        )


if __name__ == "__main__":
    main()