from functools import lru_cache
from pathlib import Path

import platformdirs
from pydantic import Field, ValidationError, ValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from .exceptions import ScopusConfigError


class ScopusSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    api_key: str = Field(alias="SCOPUS_API_KEY", min_length=1, repr=False)
    inst_token: str | None = Field(default=None, alias="SCOPUS_INST_TOKEN", repr=False)
    cache_ttl: int = Field(default=300, alias="SCOPUS_CACHE_TTL", ge=0)
    max_retries: int = Field(default=3, alias="SCOPUS_MAX_RETRIES", ge=0, le=10)
    max_wait_seconds: float = Field(default=10, alias="SCOPUS_MAX_WAIT_SECONDS", ge=0, le=60)
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    @field_validator("api_key", "inst_token")
    @classmethod
    def validate_credentials(cls, value: str | None, info: ValidationInfo) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value and info.field_name == "inst_token":
            return None
        if not value or any(c in value for c in ("\n", "\r", "\x00")):
            raise ValueError("Credential must be a non-empty single-line value.")
        return value

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        value = value.upper()
        if value not in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
            raise ValueError("Use DEBUG, INFO, WARNING, ERROR or CRITICAL.")
        return value


def user_config_path() -> Path:
    """Configuration follows the OS account, independent of working directory."""
    return Path(platformdirs.user_config_dir("scopus-mcp")) / "credentials.env"


@lru_cache(maxsize=1)
def get_settings() -> ScopusSettings:
    try:
        return ScopusSettings(_env_file=(user_config_path(), Path(".env")))
    except ValidationError as exc:
        # Never interpolate validation input: it may contain credentials.
        fields = sorted({str(e["loc"][0]) for e in exc.errors()})
        raise ScopusConfigError(
            f"Missing or invalid configuration: {', '.join(fields)}. "
            "Run `scopus setup`, or set SCOPUS_API_KEY in your environment."
        ) from exc
