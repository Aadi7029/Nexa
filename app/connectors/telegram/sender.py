# app/connectors/telegram/sender.py
import httpx
from app.core.config import settings
from typing import Any

TELEGRAM_BASE = "https://api.telegram.org"

async def send_message(chat_id: str | int, text: str) -> dict[str, Any]:
    """
    Send a message using your bot token. Returns Telegram API response JSON.
    """
    bot_token = settings.telegram_bot_token  # add this to your .env and settings
    url = f"{TELEGRAM_BASE}/bot{bot_token}/sendMessage"
    payload = {"chat_id": str(chat_id), "text": text}
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        return resp.json()
