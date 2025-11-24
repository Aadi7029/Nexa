# app/connectors/telegram/webhook.py
from typing import Any, Dict, Optional
from fastapi import APIRouter, Request, Header, HTTPException
from pydantic import BaseModel
import logging
from app.db.models import NormalizedMessage
from app.db.session import async_session
from app.tasks.enqueue import push_message_to_queue
router = APIRouter(prefix="/connectors/telegram", tags=["connectors"])
logger = logging.getLogger("nexa.telegram")


# minimal Pydantic model that tolerates common Telegram fields
class FromUser(BaseModel):
    id: Optional[int]
    is_bot: Optional[bool]
    first_name: Optional[str]
    last_name: Optional[str]
    username: Optional[str]


class Chat(BaseModel):
    id: Optional[int]
    type: Optional[str]


class Message(BaseModel):
    message_id: Optional[int]
    from_: Optional[FromUser] = None
    chat: Optional[Chat] = None
    text: Optional[str] = None
    caption: Optional[str] = None

    # alias for 'from' field in incoming JSON
    class Config:
        fields = {"from_": "from"}


class TelegramUpdate(BaseModel):
    update_id: Optional[int]
    message: Optional[Message] = None
    edited_message: Optional[Message] = None


@router.post("/webhook")
async def telegram_webhook(payload: TelegramUpdate, x_telegram_bot: Optional[str] = Header(None)):
    """
    Async handler that accepts the Telegram update and normalizes it.
    Using Pydantic keeps validation but is tolerant to missing fields.
    """
    body = payload.dict()
    msg = payload.message or payload.edited_message
    if not msg:
        logger.info("Telegram update without message received: %s", body)
        return {"ok": True, "skipped": True}

    # normalize
    platform_thread_id = str(msg.chat.id) if msg.chat and msg.chat.id is not None else None
    platform_message_id = str(msg.message_id) if msg.message_id is not None else None
    sender_id = str(msg.from_.id) if msg.from_ and msg.from_.id is not None else None
    sender_name = msg.from_.first_name if msg.from_ and msg.from_.first_name else None
    text = msg.text or msg.caption or ""

    # --- verification flow: if the incoming text matches an active verification code,
    # link the Telegram account and notify the user via the bot, then stop processing.
    from app.db.models import VerificationCode, UserPlatformAccount
    from sqlalchemy import select
    import datetime

    async with async_session() as session:
        q = await session.execute(select(VerificationCode).where(
            VerificationCode.code == text.strip(),
            VerificationCode.platform == "telegram",
            VerificationCode.used == False,
            VerificationCode.expires_at >= datetime.datetime.utcnow()
        ))
        vc = q.scalars().first()
        if vc:
            # link account: create or update UserPlatformAccount for this user
            existing_q = await session.execute(select(UserPlatformAccount).where(
                UserPlatformAccount.user_id == vc.user_id,
                UserPlatformAccount.platform == "telegram"
            ))
            existing = existing_q.scalars().first()
            if existing:
                existing.platform_user_id = sender_id
                existing.platform_chat_id = platform_thread_id
                existing.credentials = existing.credentials or {}
                session.add(existing)
            else:
                new = UserPlatformAccount(
                    user_id=vc.user_id,
                    platform="telegram",
                    platform_user_id=sender_id,
                    platform_chat_id=platform_thread_id,
                    credentials={}
                )
                session.add(new)

            # mark verification code used
            vc.used = True
            session.add(vc)
            await session.commit()
            await session.refresh(new if not existing else existing)

            # notify the user (bot replies)
            try:
                from app.connectors.telegram.sender import send_message as bot_send
                await bot_send(platform_thread_id, f"NEXA: Your account has been linked. You can now receive replies from Nexa.")
            except Exception:
                pass

            return {"ok": True, "linked": True}

    # persist
    async with async_session() as session:
        nm = NormalizedMessage(
            platform="telegram",
            platform_thread_id=platform_thread_id or "unknown",
            platform_message_id=platform_message_id or "unknown",
            sender_id=sender_id,
            sender_name=sender_name,
            text=text,
            raw_payload=body,
        )
        session.add(nm)
        await session.commit()
        await session.refresh(nm)

    # enqueue background processing (async helper inside)
    await push_message_to_queue(nm.id)

    logger.info("Stored Telegram message id=%s from=%s", nm.id, sender_name)
    return {"ok": True, "stored_id": nm.id}
