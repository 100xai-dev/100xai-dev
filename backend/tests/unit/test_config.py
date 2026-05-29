from app.config import Settings


def test_default_database_url_uses_postgres() -> None:
    settings = Settings(_env_file=None)

    assert settings.database_url == "postgresql+psycopg://100xai:100xai@localhost:5432/100xai"
