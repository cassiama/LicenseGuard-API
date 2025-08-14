from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT / ".env", env_file_encoding='utf-8')

    openai_api_key: SecretStr


if __name__ == "__main__":
    settings = Settings()
    print(settings.model_dump())
