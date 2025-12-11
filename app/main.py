# app/main.py
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import os

from app.connectors.telegram import webhook as tg_webhook
from app.api.platforms.telegram_api import router as telegram_platform_router

# Optional: frontend helper routes (create file app/api/platforms/frontend_helpers.py as suggested)
frontend_help_router = None
try:
    from app.api.platforms.frontend_helpers import router as frontend_help_router
    _HAS_FRONTEND_HELP = True
except Exception:
    _HAS_FRONTEND_HELP = False

app = FastAPI(title="NEXA API", version="0.1.0")

# CORS: allow your frontend origin(s) to call the API in dev.
# For Vite default dev server use http://localhost:5173
# In Codespaces you may need to add the forwarded URL; for quick dev using ["*"] is OK but not for prod.
_allowed_origins = os.environ.get("ALLOWED_ORIGINS", "http://localhost:5174").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,   # e.g. ["http://localhost:5173"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# include routers
app.include_router(telegram_platform_router)
app.include_router(tg_webhook.router)
if _HAS_FRONTEND_HELP and frontend_help_router is not None:
    app.include_router(frontend_help_router)


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
