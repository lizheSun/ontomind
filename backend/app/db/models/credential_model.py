"""Encrypted credential model for the Agent resource platform."""
from sqlalchemy import Boolean, Column, ForeignKey, Integer, JSON, String, Text

from app.db.models.base import BaseModel


class Credential(BaseModel):
    """A named secret whose payload is always encrypted at rest."""

    __tablename__ = "credentials"
    __table_args__ = {"comment": "Agent 平台凭据"}

    name = Column(String(128), unique=True, nullable=False, index=True)
    credential_type = Column(String(64), nullable=False, index=True)
    encrypted_payload = Column(Text, nullable=False, comment="Fernet 加密的 JSON")
    payload_keys = Column(JSON, nullable=False, default=list, comment="可安全展示的字段名")
    description = Column(String(512), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    owner_user_id = Column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )

    def to_response_dict(self) -> dict:
        """Return metadata with masked values and never expose ciphertext."""
        return {
            "id": self.id,
            "name": self.name,
            "credential_type": self.credential_type,
            "payload": {key: "********" for key in (self.payload_keys or [])},
            "description": self.description,
            "is_active": bool(self.is_active),
            "owner_user_id": self.owner_user_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


__all__ = ["Credential"]
