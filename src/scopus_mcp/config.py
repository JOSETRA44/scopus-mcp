from functools import lru_cache

from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

from .exceptions import ScopusConfigError


class ScopusSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    api_key: str = Field(alias="SCOPUS_API_KEY")
    inst_token: str | None = Field(default=None, alias="SCOPUS_INST_TOKEN")
    cache_ttl: int = Field(default=300, alias="SCOPUS_CACHE_TTL", ge=0)
    max_retries: int = Field(default=3, alias="SCOPUS_MAX_RETRIES", ge=0, le=10)
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")


@lru_cache(maxsize=1)
def get_settings() -> ScopusSettings:
    try:
        return ScopusSettings()
    except ValidationError as exc:
        missing = [e["loc"][0] for e in exc.errors() if e["type"] == "missing"]
        raise ScopusConfigError(
            f"Missing required environment variable(s): {', '.join(str(m) for m in missing)}. "
            "Set SCOPUS_API_KEY in your environment or in a .env file."
        ) from exc
