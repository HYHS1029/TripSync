from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr, field_validator
from urllib.parse import urlsplit
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    jwt_secret_key: SecretStr = Field(min_length=32)
    access_token_expire_minutes: int = Field(default=30, gt=0, le=1440)
    google_maps_api_key: SecretStr | None = None
    cors_allow_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    @field_validator("cors_allow_origins")
    @classmethod
    def validate_origins(cls, origins: list[str]) -> list[str]:
        result = []
        for origin in origins:
            parsed = urlsplit(origin)
            if (
                parsed.scheme not in {"http", "https"} or not parsed.hostname
                or parsed.username or parsed.password
                or parsed.path not in {"", "/"} or parsed.query or parsed.fragment
                or "*" in parsed.netloc
            ):
                raise ValueError("CORS origins must be explicit HTTP(S) origins without paths")
            result.append(origin.rstrip("/"))
        return result


@lru_cache
def get_settings() -> Settings:
    return Settings()
