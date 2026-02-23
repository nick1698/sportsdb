from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    app_name: str = "SportsDB API"
    log_level: str = "INFO"

    # Keep it optional for now (we haven't implemented DB yet)
    database_url: str | None = None


settings = Settings()
