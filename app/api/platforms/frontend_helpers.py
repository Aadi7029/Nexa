
# app/api/platforms/frontend_helpers.py

from fastapi import APIRouter



router = APIRouter(prefix="/api/frontend", tags=["frontend"])



@router.get("/config")

async def get_frontend_config():

    """Return frontend configuration"""

    return {"status": "ok"}

