from app.config import build_database_url_from_postgres


def test_build_database_url_encodes_password_for_url():
    url = build_database_url_from_postgres(
        "user",
        "p@:s%word",
        "db.internal",
        5432,
        "mydb",
    )
    assert url.startswith("postgresql+asyncpg://")
    assert "p@:s%word" not in url
    assert "db.internal:5432/mydb" in url
