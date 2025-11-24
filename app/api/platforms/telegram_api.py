# app/api/platforms/telegram_api.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.db.session import async_session
from app.db.models import UserPlatformAccount, VerificationCode, User
import random, string, datetime
from sqlalchemy import select
from app.connectors.telegram.sender import send_message
from datetime import datetime,timedelta
router = APIRouter(prefix="/platforms/telegram", tags=["platforms"])

def generate_code(n=6):
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=n))

# --- request link (create a code) ---
class RequestLinkIn(BaseModel):
    user_id: int   # in prod use auth; here we accept user_id for simplicity

class RequestLinkOut(BaseModel):
    code: str
    instructions: str

@router.post("/request_link", response_model=RequestLinkOut)
async def request_link(payload: RequestLinkIn):
    """
    Called from client: create a code the user must send to the Telegram bot.
    """
    async with async_session() as session:
        # verify user exists
        user = await session.get(User, payload.user_id)
        if not user:
            raise HTTPException(status_code=404, detail="user not found")
        code = generate_code()
        expires = datetime.datetime.utcnow() + datetime.timedelta(minutes=15)
        vc = VerificationCode(user_id=payload.user_id, platform="telegram", code=code, expires_at=expires)
        session.add(vc)
        await session.commit()
        await session.refresh(vc)

    instructions = (
        f"Open Telegram and send the code `{code}` to the Nexa bot. "
        "Once the bot receives it, your Telegram account will be linked to your Nexa account."
    )
    return {"code": code, "instructions": instructions}


# --- send message (app -> telegram) ---
class SendMessageIn(BaseModel):
    user_id: int   # authenticated Nexa user
    text: str

@router.post("/send")
async def send_message_route(payload: SendMessageIn):
    """
    Send a message to the user's linked Telegram chat.
    """
    async with async_session() as session:
        q = await session.execute(select(UserPlatformAccount).where(
            UserPlatformAccount.user_id == payload.user_id,
            UserPlatformAccount.platform == "telegram"
        ))
        acct = q.scalars().first()
        if not acct:
            raise HTTPException(status_code=404, detail="telegram account not linked")

        # perform send
        resp = await send_message(acct.platform_chat_id, payload.text)

        # optionally log the outgoing message somewhere (omitted here)
        return {"ok": True, "telegram_response": resp}


# --- unlink / deboard ---
class UnlinkIn(BaseModel):
    user_id: int

@router.post("/unlink")
async def unlink(payload: UnlinkIn):
    async with async_session() as session:
        q = await session.execute(select(UserPlatformAccount).where(
            UserPlatformAccount.user_id == payload.user_id,
            UserPlatformAccount.platform == "telegram"
        ))
        acct = q.scalars().first()
        if not acct:
            raise HTTPException(status_code=404, detail="not linked")
        await session.delete(acct)
        await session.commit()
    return {"ok": True, "detail": "telegram unlinked"}
