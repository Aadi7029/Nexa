# app/main.py
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import os
from app.connectors.telegram import webhook as tg_webhook
from app.api.platforms.telegram_api import router as telegram_platform_router
app = FastAPI(title="NEXA API", version="0.1.0")
app.include_router(telegram_platform_router)
app.include_router(tg_webhook.router)
@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/webhook/{platform}")
async def receive_webhook(platform: str, request: Request):
    """
    Generic webhook receiver for platform connectors.
    Platform-specific connector logic will validate and normalize payload.
    """
    payload = await request.json()
    # TODO: push into queue / normalize and store
    return JSONResponse({"received_from": platform, "ok": True})

# app = FastAPI(title="NEXA API")