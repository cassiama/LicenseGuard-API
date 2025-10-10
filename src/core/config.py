from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL
from pathlib import Path
from secrets import token_hex

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT / ".env", env_file_encoding='utf-8')

    openai_api_key: SecretStr | None = None
    jwt_secret_key: str | None = token_hex(16)
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    db_url: str | URL | None = None


def get_settings() -> Settings:
    return Settings()


if __name__ == "__main__":
    settings = get_settings()
    print(settings.model_dump())
