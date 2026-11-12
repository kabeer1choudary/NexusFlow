from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="NXFLOW_", env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://nxflow:nxflow@localhost:5432/nxflow"
    api_key: str | None = None
    sql_echo: bool = False


settings = Settings()
