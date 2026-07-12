"""Credential request/response schemas."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator


class CredentialCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    credential_type: str = Field(..., min_length=1, max_length=64)
    payload: dict[str, Any]
    description: str | None = Field(default=None, max_length=512)
    is_active: bool = True

    @field_validator("payload")
    @classmethod
    def payload_must_not_be_empty(cls, value: dict[str, Any]) -> dict[str, Any]:
        if not value:
            raise ValueError("payload 不能为空")
        return value


class CredentialUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    credential_type: str | None = Field(default=None, min_length=1, max_length=64)
    payload: dict[str, Any] | None = None
    description: str | None = Field(default=None, max_length=512)
    is_active: bool | None = None

    @field_validator("payload")
    @classmethod
    def payload_must_not_be_empty(
        cls, value: dict[str, Any] | None
    ) -> dict[str, Any] | None:
        if value is not None and not value:
            raise ValueError("payload 不能为空")
        return value


class CredentialResponse(BaseModel):
    id: int
    name: str
    credential_type: str
    payload: dict[str, str]
    description: str | None = None
    is_active: bool
    owner_user_id: int
    created_at: str | None = None
    updated_at: str | None = None


__all__ = ["CredentialCreate", "CredentialResponse", "CredentialUpdate"]
