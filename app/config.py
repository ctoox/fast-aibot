from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    base_url: str = "https://ilinkai.weixin.qq.com"
    token_path: str = "~/.weixin-bot/credentials.json"
    host: str = "0.0.0.0"
    port: int = 8080
    debug: bool = False
    webhook_url: str | None = None

    model_config = SettingsConfigDict(
        env_prefix="WEIXIN_BOT_",
        env_file=".env",
        env_file_encoding="utf-8",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
