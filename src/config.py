from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    postgres_user: str = "mi_user"
    postgres_password: str = "mi_password"
    postgres_db: str = "market_intelligence"
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # LINDAS SPARQL endpoint (official Swiss Linked Data)
    lindas_sparql_url: str = "https://lindas.admin.ch/query"
    lindas_request_delay: float = 0.5  # seconds between batch requests

    model_config = {"env_file": ".env", "extra": "ignore"}

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def database_url_sync(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()
