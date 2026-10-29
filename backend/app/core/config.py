from functools import lru_cache
from pathlib import Path

from typing import Literal

from pydantic import EmailStr, Field, SecretStr, field_validator, model_validator
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
    frontend_url: str = "http://localhost:3000"
    email_verification_enabled: bool = False
    email_verification_expire_minutes: int = Field(default=30, ge=5, le=1440)
    smtp_host: str | None = None
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_security: Literal["starttls", "ssl", "none"] = "starttls"
    smtp_username: str | None = None
    smtp_password: SecretStr | None = None
    smtp_from_email: EmailStr = "noreply@tripsync.example"

    @field_validator("frontend_url")
    @classmethod
    def validate_frontend_url(cls, value: str) -> str:
        parsed = urlsplit(value)
        if (parsed.scheme not in {"http", "https"} or not parsed.hostname
                or parsed.username or parsed.password or parsed.path not in {"", "/"}
                or parsed.query or parsed.fragment or "*" in parsed.netloc
                or any(character.isspace() for character in value)
                or (parsed.scheme == "http" and parsed.hostname not in {"localhost", "127.0.0.1", "::1"})):
            raise ValueError("FRONTEND_URL must be an HTTPS origin (HTTP is local-only)")
        return value.rstrip("/")

    @model_validator(mode="after")
    def validate_smtp(self):
        if self.smtp_host and self.smtp_security == "none" and self.smtp_host not in {"localhost", "127.0.0.1", "::1"}:
            raise ValueError("Unencrypted SMTP is only allowed on loopback")
        if bool(self.smtp_username) != bool(self.smtp_password):
            raise ValueError("SMTP username and password must be configured together")
        return self

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
