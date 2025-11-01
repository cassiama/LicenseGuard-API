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
    jwt_secret_key: SecretStr = SecretStr(token_hex(16))
    jwt_algorithm: SecretStr = SecretStr("HS256")
    user_access_token_expire_minutes: int = 30
    db_url: str | URL | None = None
    jwt_audience: SecretStr = SecretStr("licenseguard-api")
    mcp_client_id: SecretStr | None = None
    mcp_client_secret: SecretStr | None = None
    mcp_access_token_expire_minutes: int = 10
    # must be a string of space-delimited scopes
    mcp_required_scopes: SecretStr = SecretStr("analyze:run")


def get_settings() -> Settings:
    return Settings()


if __name__ == "__main__":
    settings = get_settings()
    print(settings.model_dump())
