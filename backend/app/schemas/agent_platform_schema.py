"""节点连接与发现 API DTO。"""
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, model_validator


class NodeConnectionCreate(BaseModel):
    connector_type: Literal["local", "ssh"]
    address: str | None = Field(None, max_length=255)
    port: int | None = Field(None, ge=1, le=65535)
    username: str | None = Field(None, max_length=128)
    credential_id: int | None = Field(None, ge=1)
    password: str | None = Field(None, max_length=4096)
    private_key: str | None = Field(None, max_length=65536)
    host_key_algorithm: str | None = Field(None, max_length=64)
    host_key_fingerprint: str | None = Field(None, max_length=255)
    managed_roots: list[str] = Field(min_length=1, max_length=16)
    connect_timeout_seconds: int = Field(10, ge=1, le=60)
    command_timeout_seconds: int = Field(30, ge=1, le=120)
    max_concurrency: int = Field(2, ge=1, le=16)

    @model_validator(mode="after")
    def validate_ssh(self):
        if self.connector_type == "ssh":
            required = {
                "address": self.address,
                "username": self.username,
            }
            missing = [key for key, value in required.items() if not value]
            if missing:
                raise ValueError(f"SSH connection requires: {', '.join(missing)}")
            if bool(self.host_key_algorithm) != bool(self.host_key_fingerprint):
                raise ValueError("host key algorithm and fingerprint must be supplied together")
            if self.credential_id and (self.password or self.private_key):
                raise ValueError("credential_id cannot be combined with inline credentials")
        return self


class NodeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    hostname: str | None = Field(None, max_length=255)
    platform: str | None = Field(None, max_length=64)
    labels: dict[str, Any] | None = None
    connection: NodeConnectionCreate


class DiscoveryCreate(BaseModel):
    provider_type: Literal["opencode"] = "opencode"


class DiscoveryDecision(BaseModel):
    decision: Literal["import", "link", "keep_platform", "ignore", "external"]


class DiscoveryApply(BaseModel):
    item_ids: list[int] | None = None


class HostKeyConfirmation(BaseModel):
    host_key_algorithm: str = Field(min_length=1, max_length=64)
    host_key_fingerprint: str = Field(min_length=1, max_length=255)
    reason: str = Field(min_length=1, max_length=512)


# Unified Agent lifecycle and Run domain DTOs.


class AgentCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    type: str = "custom_looper"
    description: Optional[str] = None
    config: dict[str, Any] = Field(default_factory=dict)
    version_note: Optional[str] = None


class AgentUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=128)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class VersionCreateRequest(BaseModel):
    config: dict[str, Any]
    note: Optional[str] = Field(default=None, max_length=256)


class VersionLoadRequest(BaseModel):
    environment: str = Field(default="default", min_length=1, max_length=64)
    runtime_config: dict[str, Any] = Field(default_factory=dict)


class DeploymentCreateRequest(BaseModel):
    agent_version_id: int = Field(ge=1)
    environment: str = Field(default="default", min_length=1, max_length=64)
    runtime_config: dict[str, Any] = Field(default_factory=dict)


class DeploymentTransitionRequest(BaseModel):
    action: Literal[
        "start", "activate", "fail", "stop", "drain", "force_offline"
    ]
    expected_version: Optional[int] = Field(default=None, ge=1)


class DeploymentControlRequest(BaseModel):
    expected_version: Optional[int] = Field(default=None, ge=1)
    reason: Optional[str] = Field(default=None, max_length=512)
    target_version_id: Optional[int] = Field(default=None, ge=1)


class SessionCreateRequest(BaseModel):
    agent_id: int = Field(ge=1)
    deployment_id: Optional[int] = Field(default=None, ge=1)
    title: Optional[str] = Field(default=None, max_length=256)
    metadata: dict[str, Any] = Field(default_factory=dict)


class MessageCreateRequest(BaseModel):
    role: Literal["user"] = "user"
    content: str = Field(min_length=1)
    content_type: Literal["text", "markdown", "json"] = "text"
    metadata: dict[str, Any] = Field(default_factory=dict)


class RunCreateRequest(BaseModel):
    agent_version_id: int = Field(ge=1)
    deployment_id: Optional[int] = Field(default=None, ge=1)
    session_id: Optional[int] = Field(default=None, ge=1)
    strategy: Literal["single_shot", "evaluator_optimizer"] = "single_shot"
    kind: Literal["chat", "job", "eval", "discovery", "deployment"] = "chat"
    input: dict[str, Any] = Field(default_factory=dict)


class RunControlRequest(BaseModel):
    action: Literal["start", "pause", "resume", "retry", "cancel"]
    expected_version: Optional[int] = Field(default=None, ge=1)


class RunActionRequest(BaseModel):
    expected_version: Optional[int] = Field(default=None, ge=1)


class ApprovalCreateRequest(BaseModel):
    run_id: int = Field(ge=1)
    step_id: Optional[int] = Field(default=None, ge=1)
    tool_name: str = Field(min_length=1, max_length=128)
    arguments: dict[str, Any] = Field(default_factory=dict)


class ApprovalDecisionRequest(BaseModel):
    decision: Literal["approve", "reject"]
    expected_version: int = Field(ge=1)
    reason: Optional[str] = None
