# app/db/models.py
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = sa.Column(sa.Integer, primary_key=True, index=True)
    email = sa.Column(sa.String, unique=True, nullable=True)
    # add more fields as you need

class UserPlatformAccount(Base):
    __tablename__ = "user_platform_accounts"
    id = sa.Column(sa.Integer, primary_key=True, index=True)
    user_id = sa.Column(sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    platform = sa.Column(sa.String, nullable=False, index=True)  # e.g. 'telegram'
    platform_user_id = sa.Column(sa.String, nullable=False)       # e.g. telegram user id
    platform_chat_id = sa.Column(sa.String, nullable=True)        # e.g. chat id
    credentials = sa.Column(sa.JSON, nullable=True)               # encrypted token metadata for OAuth platforms
    created_at = sa.Column(sa.DateTime(timezone=True), server_default=sa.func.now())
    updated_at = sa.Column(sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now())

    user = relationship("User", backref="platform_accounts")


class VerificationCode(Base):
    __tablename__ = "verification_codes"
    id = sa.Column(sa.Integer, primary_key=True, index=True)
    user_id = sa.Column(sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    platform = sa.Column(sa.String, nullable=False)
    code = sa.Column(sa.String, nullable=False, index=True)
    used = sa.Column(sa.Boolean, default=False)
    created_at = sa.Column(sa.DateTime(timezone=True), server_default=sa.func.now())
    expires_at = sa.Column(sa.DateTime(timezone=True), nullable=True)

    user = relationship("User", backref="verification_codes")

class NormalizedMessage(Base, AsyncAttrs):
    __tablename__ = "normalized_messages"

    id = sa.Column(sa.Integer, primary_key=True, index=True)
    platform = sa.Column(sa.String, nullable=False, index=True)
    platform_thread_id = sa.Column(sa.String, nullable=False, index=True)
    platform_message_id = sa.Column(sa.String, nullable=False)
    sender_id = sa.Column(sa.String, nullable=True)
    sender_name = sa.Column(sa.String, nullable=True)
    text = sa.Column(sa.Text, nullable=True)
    raw_payload = sa.Column(JSONB, nullable=True)
    created_at = sa.Column(sa.DateTime(timezone=True), default=datetime.utcnow)
    processed = sa.Column(sa.Boolean, default=False, index=True)
