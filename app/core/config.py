# app/core/config.py
from __future__ import annotations
from typing import Optional, Dict, Any

# --- detect runtime pydantic version / availability ---
_is_pydantic_v2 = False
try:
    import pydantic as _pydantic  # type: ignore
    _ver = getattr(_pydantic, "__version__", "")
    if _ver:
        _is_pydantic_v2 = int(_ver.split(".", 1)[0]) >= 2
except Exception:
    _is_pydantic_v2 = False

try:
    import pydantic_settings  # type: ignore
    _is_pydantic_v2 = True
except Exception:
    pass

# --- import the right BaseSettings ---
if _is_pydantic_v2:
    try:
        from pydantic_settings import BaseSettings  # type: ignore
    except Exception as exc:
        raise RuntimeError(
            "Detected Pydantic v2 but 'pydantic-settings' (BaseSettings) is not available.\n"
            "Install it with: pip install pydantic-settings\n"
        ) from exc
else:
    from pydantic import BaseSettings  # type: ignore

# --- defaults & annotations ---
_DEFAULTS: Dict[str, Any] = {
    "env": "dev",
    "openai_api_key": None,
    "openai_model": "gpt-5-1",
    "telegram_bot_token": None,
    "webhook_base_url": None,
    "telegram_webhook_url": None,
    "redis_url": "redis://localhost:6379/0",
}

if _is_pydantic_v2:
    # Create a v2-only Settings class dynamically
    annotations = {
        "env": str,
        "database_url": str,
        "redis_url": str,
        "openai_api_key": Optional[str],
        "openai_model": Optional[str],
        "telegram_bot_token": Optional[str],
        "webhook_base_url": Optional[str],
        "telegram_webhook_url": Optional[str],
    }
    attrs: Dict[str, Any] = {
        "__annotations__": annotations,
        "env": _DEFAULTS["env"],
        "openai_api_key": _DEFAULTS["openai_api_key"],
        "openai_model": _DEFAULTS["openai_model"],
        "telegram_bot_token": _DEFAULTS["telegram_bot_token"],
        "webhook_base_url": _DEFAULTS["webhook_base_url"],
        "telegram_webhook_url": _DEFAULTS["telegram_webhook_url"],
        "redis_url": _DEFAULTS["redis_url"],
        "model_config": {
            "env_file": ".env",
            "env_file_encoding": "utf-8",
            "extra": "ignore",
            "case_sensitive": False,
        },
    }
    Settings = type("Settings", (BaseSettings,), attrs)  # type: ignore
else:
    class Settings(BaseSettings):  # type: ignore
        env: str = _DEFAULTS["env"]
        database_url: str
        redis_url: str = _DEFAULTS["redis_url"]
        openai_api_key: Optional[str] = _DEFAULTS["openai_api_key"]
        openai_model: Optional[str] = _DEFAULTS["openai_model"]
        telegram_bot_token: Optional[str] = _DEFAULTS["telegram_bot_token"]
        webhook_base_url: Optional[str] = _DEFAULTS["webhook_base_url"]
        telegram_webhook_url: Optional[str] = _DEFAULTS["telegram_webhook_url"]

        class Config:
            env_file = ".env"
            env_file_encoding = "utf-8"
            extra = "ignore"

# module-level instance
settings = Settings()
