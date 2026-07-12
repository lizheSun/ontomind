"""Encrypted credential management service."""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.core import crypto
from app.core.exceptions import ConflictException, NotFoundException, ValidationException
from app.db.models.credential_model import Credential
from app.db.repositories.credential_repo import CredentialRepository
from app.schemas.audit_log_schema import AuditLogCreate
from app.schemas.credential_schema import CredentialCreate, CredentialUpdate
from app.services.audit_log_service import AuditLogService


class CredentialService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = CredentialRepository(db)
        self.audit = AuditLogService(db)

    @staticmethod
    def _encrypt_payload(payload: dict[str, Any]) -> str:
        try:
            plaintext = json.dumps(
                payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True
            )
        except (TypeError, ValueError) as exc:
            raise ValidationException("credential payload 必须可序列化为 JSON") from exc
        try:
            crypto.require_key_or_raise()
            return crypto.encrypt(plaintext)
        except RuntimeError as exc:
            raise ValidationException(str(exc), code="ENCRYPTION_NOT_CONFIGURED") from exc

    def _record(
        self,
        action: str,
        credential_id: int,
        actor_user_id: int,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.audit.record(
            AuditLogCreate(
                actor_user_id=actor_user_id,
                action=action,
                resource_type="credential",
                resource_id=str(credential_id),
                details=details,
            )
        )

    def create(self, data: CredentialCreate, actor_user_id: int) -> dict:
        if self.repo.name_exists(data.name):
            raise ConflictException("凭据名称已存在", code="CREDENTIAL_NAME_EXISTS")
        row = self.repo.create(
            {
                "name": data.name,
                "credential_type": data.credential_type,
                "encrypted_payload": self._encrypt_payload(data.payload),
                "payload_keys": sorted(data.payload.keys()),
                "description": data.description,
                "is_active": data.is_active,
                "owner_user_id": actor_user_id,
            }
        )
        self._record(
            "credential.create",
            row.id,
            actor_user_id,
            {"name": row.name, "credential_type": row.credential_type},
        )
        self.db.commit()
        self.db.refresh(row)
        return row.to_response_dict()

    def get(self, credential_id: int) -> dict:
        return self._get_or_raise(credential_id).to_response_dict()

    def list(self, skip: int = 0, limit: int = 100) -> list[dict]:
        return [row.to_response_dict() for row in self.repo.get_all(skip, limit)]

    def update(
        self, credential_id: int, data: CredentialUpdate, actor_user_id: int
    ) -> dict:
        self._get_or_raise(credential_id)
        values = data.model_dump(exclude_unset=True)
        if "name" in values and self.repo.name_exists(
            values["name"], exclude_id=credential_id
        ):
            raise ConflictException("凭据名称已存在", code="CREDENTIAL_NAME_EXISTS")
        payload = values.pop("payload", None)
        if payload is not None:
            values["encrypted_payload"] = self._encrypt_payload(payload)
            values["payload_keys"] = sorted(payload.keys())
        updated = self.repo.update(credential_id, values)
        assert updated is not None
        self._record(
            "credential.update",
            credential_id,
            actor_user_id,
            {"changed_fields": sorted(data.model_fields_set - {"payload"})},
        )
        self.db.commit()
        self.db.refresh(updated)
        return updated.to_response_dict()

    def delete(self, credential_id: int, actor_user_id: int) -> None:
        row = self._get_or_raise(credential_id)
        safe_details = {"name": row.name, "credential_type": row.credential_type}
        self.repo.delete(credential_id)
        self._record("credential.delete", credential_id, actor_user_id, safe_details)
        self.db.commit()

    def decrypt_payload_for_use(self, credential_id: int) -> dict[str, Any]:
        """Internal-only secret access; API responses must never call this."""
        row = self._get_or_raise(credential_id)
        return json.loads(crypto.decrypt(row.encrypted_payload))

    def _get_or_raise(self, credential_id: int) -> Credential:
        row = self.repo.get_by_id(credential_id)
        if not row:
            raise NotFoundException(
                f"凭据不存在: {credential_id}", code="CREDENTIAL_NOT_FOUND"
            )
        return row


__all__ = ["CredentialService"]
