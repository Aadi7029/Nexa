# app/api/admin/messages.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from app.db.models import NormalizedMessage, UserPlatformAccount
from sqlalchemy import select
from app.db.session import async_session
from app.connectors.telegram.sender import send_message  # existing send helper

router = APIRouter(prefix="/admin/messages", tags=["admin"])

class ReplyIn(BaseModel):
    text: str
    send_auto: bool = False  # future use (auto reply)

@router.get("/", response_model=List[dict])
async def list_pending(limit: int = 50):
    async with async_session() as session:
        q = await session.execute(
            select(NormalizedMessage).where(NormalizedMessage.status == "pending").order_by(NormalizedMessage.created_at.desc()).limit(limit)
        )
        rows = q.scalars().all()
        return [
            {
                "id": r.id,
                "sender_id": r.sender_id,
                "sender_name": r.sender_name,
                "text": r.text,
                "created_at": r.created_at,
            }
            for r in rows
        ]

@router.post("/{message_id}/reply")
async def reply_message(message_id: int, body: ReplyIn):
    # fetch record and send via telegram sender
    async with async_session() as session:
        nm = await session.get(NormalizedMessage, message_id)
        if not nm:
            raise HTTPException(status_code=404, detail="message not found")
        # find platform_chat_id from user_platform_accounts (if linked)
        q = await session.execute(select(UserPlatformAccount).where(UserPlatformAccount.platform_chat_id == nm.platform_thread_id))
        # fall back to platform_user_id if needed
        up = q.scalars().first()
        chat_id = up.platform_chat_id if up else nm.platform_thread_id

        # call existing send function (can be async)
        try:
            await send_message(chat_id, body.text)  # if send_message is async; adapt if sync
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))

        # mark message as responded
        nm.status = "responded"
        session.add(nm)
        await session.commit()
        return {"ok": True, "message_id": nm.id, "status": nm.status}
