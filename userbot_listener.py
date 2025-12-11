# userbot_listener.py
import os
import sys
import json
import logging
import requests
import asyncio
from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError
from aiohttp import web

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("userbot")

# Config from env
API_ID = int(os.environ.get("TG_API_ID", "0"))
API_HASH = os.environ.get("TG_API_HASH", "")
PHONE = os.environ.get("TG_PHONE", "")  # only needed first-run
BACKEND_WEBHOOK = os.environ.get("BACKEND_WEBHOOK", "http://127.0.0.1:8000/connectors/personal/webhook")
SESSION_NAME = os.environ.get("TG_SESSION", "user_session")
# HTTP server config for inbound reply requests (from your backend)
HTTP_HOST = os.environ.get("USERBOT_HTTP_HOST", "127.0.0.1")
HTTP_PORT = int(os.environ.get("USERBOT_HTTP_PORT", "9000"))
# Shared secret header to authorize backend -> userbot calls
INCOMING_SECRET = os.environ.get("USERBOT_SECRET", "change-me-to-a-strong-secret")

if not API_ID or not API_HASH:
    logger.error("TG_API_ID and TG_API_HASH must be set in environment.")
    sys.exit(1)

client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

# Helper: forward to backend (when receiving personal messages)
def forward_to_backend(payload: dict, max_retries: int = 3):
    headers = {"Content-Type": "application/json"}
    for attempt in range(1, max_retries + 1):
        try:
            r = requests.post(BACKEND_WEBHOOK, json=payload, headers=headers, timeout=10)
            r.raise_for_status()
            logger.info("Forwarded message id=%s -> backend (status=%s)", payload.get("message_id"), r.status_code)
            return True
        except Exception as exc:
            logger.warning("Failed to forward (attempt %s/%s): %s", attempt, max_retries, exc)
            if attempt < max_retries:
                import time; time.sleep(1.5 * attempt)
            else:
                logger.error("Giving up forwarding message id=%s", payload.get("message_id"))
                return False

@client.on(events.NewMessage(incoming=True))
async def handler(event):
    if event.out:
        return
    try:
        sender = await event.get_sender()
        chat = await event.get_chat()
    except Exception:
        sender = None
        chat = None

    payload = {
        "update_id": None,
        "message": {
            "message_id": event.message.id if event.message else None,
            "from": {
                "id": getattr(sender, "id", None),
                "is_bot": getattr(sender, "bot", False) if sender else False,
                "first_name": getattr(sender, "first_name", None),
                "username": getattr(sender, "username", None),
            },
            "chat": {
                "id": getattr(chat, "id", None) if chat else getattr(sender, "id", None),
                "type": "private" if event.is_private else "group"
            },
            "date": int(event.message.date.timestamp()) if event.message and event.message.date else None,
            "text": event.message.message if event.message else None,
            "raw": event.message.to_json() if event.message else None
        }
    }

    logger.info("Received personal DM from %s: %r", payload["message"]["from"].get("username") or payload["message"]["from"].get("id"), (payload["message"]["text"] or "")[:120])
    forward_to_backend(payload)

# -----------------------
# aiohttp: /send_reply
# -----------------------
# This endpoint accepts POST JSON:
# { "chat_id": "<chat id>", "text": "reply text" }
# or alternatively:
# { "message_id": <normalized_message_id>, "text": "reply text" }
# The backend should supply header "X-USERBOT-SECRET: <secret>"
async def send_reply_handler(request):
    # auth
    secret = request.headers.get("X-USERBOT-SECRET", "")
    if not secret or secret != INCOMING_SECRET:
        return web.json_response({"error": "unauthorized"}, status=401)

    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "invalid json"}, status=400)

    text = data.get("text")
    if not text:
        return web.json_response({"error": "text required"}, status=400)

    # Accept either chat_id directly, or a normalized_message_id that the userbot cannot resolve itself.
    chat_id = data.get("chat_id")
    # Optional: allow sending to normalized_message's platform_thread_id if backend passes it instead.
    # If chat_id is numeric string, Telethon is happy with int or str.
    try:
        if not chat_id:
            return web.json_response({"error": "chat_id required"}, status=400)

        # Send message via Telethon
        # client.send_message is a coroutine
        await client.send_message(entity=chat_id, message=text)
        logger.info("Sent reply to chat_id=%s text=%r", chat_id, text[:120])
        return web.json_response({"ok": True})
    except Exception as exc:
        logger.exception("Failed to send reply via userbot")
        return web.json_response({"error": str(exc)}, status=500)

# A small web app runner that runs in same asyncio loop as Telethon
async def start_webapp(app):
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, HTTP_HOST, HTTP_PORT)
    await site.start()
    logger.info("Userbot HTTP server listening on http://%s:%s", HTTP_HOST, HTTP_PORT)
    return runner

async def main():
    # Start Telethon client
    try:
        await client.start(phone=PHONE if PHONE else None)
    except SessionPasswordNeededError:
        logger.error("Two-step verification enabled. Please supply your password interactively.")
        await client.disconnect()
        return

    me = await client.get_me()
    logger.info("Userbot started as %s (id=%s)", getattr(me, "username", None), getattr(me, "id", None))

    # Create aiohttp app and route
    app = web.Application()
    app.router.add_post("/send_reply", send_reply_handler)

    # Start the webapp in background (same event loop)
    await start_webapp(app)

    # Run until disconnected
    await client.run_until_disconnected()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Exiting userbot.")
