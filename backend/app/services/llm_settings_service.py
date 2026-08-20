"""平台 LLM 配置：多套配置 + DB 优先，.env 兜底。

设计约定（避免歧义）：
- `enabled`    该配置是否可用（停用后不可被「应用」，但保留数据）。
- `is_default` 全局唯一的「当前生效」标记：标注/本体生成等 LLM 任务只认这一条。
- 「应用 / 设为默认」= 把某条置为 is_default=True 并自动 enabled=True，同时清除其它默认。
- 停用当前默认配置时，自动取消其 is_default（避免「默认但已停用」的歧义状态）。
- 若没有 is_default 且 enabled 的配置，`resolve_llm_client` 回退到 `.env`。
"""
from __future__ import annotations

import base64
import hashlib
import time
from typing import Optional

from cryptography.fernet import Fernet
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import BusinessException, NotFoundException
from app.db.models.meta_model import PlatformLlmSetting
from app.db.repositories.meta_repo import PlatformLlmSettingRepository
from app.schemas.metadata_schema import (
    LlmSettingCreate,
    LlmSettingResponse,
    LlmSettingTestRequest,
    LlmSettingUpdate,
)
from app.services.llm_client import LLMClient


def _cipher() -> Fernet:
    key = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def _encrypt(plain: str) -> str:
    if not plain:
        return ""
    return _cipher().encrypt(plain.encode()).decode()


def _decrypt(cipher: str) -> str:
    if not cipher:
        return ""
    return _cipher().decrypt(cipher.encode()).decode()


def _mask(key: str) -> Optional[str]:
    if not key:
        return None
    if len(key) <= 8:
        return "****"
    return f"{key[:4]}****{key[-4:]}"


def _build_client(
    *,
    base_url: str,
    model: str,
    api_key: str,
    timeout: Optional[int] = None,
) -> LLMClient:
    return LLMClient(
        base_url=base_url or settings.LLM_BASE_URL,
        api_key=api_key,
        model=model or settings.LLM_MODEL,
        timeout=timeout if timeout is not None else settings.LLM_TIMEOUT,
    )


def resolve_llm_client(db: Optional[Session] = None) -> LLMClient:
    """返回当前生效的 LLM 客户端：DB 默认配置优先，.env 兜底。"""
    if db is not None:
        row = PlatformLlmSettingRepository(db).get_default()
        if row:
            api_key = ""
            try:
                api_key = _decrypt(row.api_key_encrypted or "")
            except Exception:
                api_key = ""
            if api_key and (row.model or "").strip():
                return _build_client(
                    base_url=row.base_url,
                    model=row.model,
                    api_key=api_key,
                    timeout=row.timeout,
                )
    return LLMClient()


class LlmSettingsService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = PlatformLlmSettingRepository(db)

    # ---------- 序列化 ----------

    def _to_response(self, row: PlatformLlmSetting) -> LlmSettingResponse:
        key = ""
        try:
            key = _decrypt(row.api_key_encrypted or "")
        except Exception:
            key = ""
        configured = bool(key and (row.model or "").strip() and row.enabled)
        return LlmSettingResponse(
            id=row.id,
            name=row.name or "",
            base_url=row.base_url or "",
            model=row.model or "",
            api_key_masked=_mask(key),
            has_api_key=bool(key),
            timeout=int(row.timeout or 120),
            max_concurrency=int(row.max_concurrency or 4),
            enabled=bool(row.enabled),
            is_default=bool(row.is_default),
            source="db",
            configured=configured,
        )

    def _env_response(self) -> LlmSettingResponse:
        env_key = settings.LLM_API_KEY or ""
        configured = bool(env_key.strip() and (settings.LLM_MODEL or "").strip())
        return LlmSettingResponse(
            id=0,
            name=".env 兜底",
            base_url=settings.LLM_BASE_URL or "",
            model=settings.LLM_MODEL or "",
            api_key_masked=_mask(env_key) if env_key else None,
            has_api_key=bool(env_key.strip()),
            timeout=int(settings.LLM_TIMEOUT or 120),
            max_concurrency=int(settings.LLM_MAX_CONCURRENCY or 4),
            enabled=True,
            is_default=False,
            source="env" if configured else "none",
            configured=configured,
        )

    # ---------- 查询 ----------

    def list(self) -> list[LlmSettingResponse]:
        rows = self.repo.list_all()
        out = [self._to_response(r) for r in rows]
        # 无 DB 配置时返回 .env 兜底项，让前端知道当前可用来源
        if not rows:
            out.append(self._env_response())
        return out

    def get(self, setting_id: int) -> LlmSettingResponse:
        row = self.repo.get(setting_id)
        if not row:
            raise NotFoundException(f"LLM 配置不存在: {setting_id}")
        return self._to_response(row)

    def get_active(self) -> LlmSettingResponse:
        row = self.repo.get_default()
        if row:
            return self._to_response(row)
        return self._env_response()

    # ---------- 写操作 ----------

    def create(self, data: LlmSettingCreate, user_id: Optional[int] = None) -> LlmSettingResponse:
        key = (data.api_key or "").strip()
        if not key:
            raise BusinessException("API Key 不能为空", code="LLM_KEY_REQUIRED")
        row = PlatformLlmSetting(
            name=(data.name or "").strip() or self._default_name(data.model),
            base_url=(data.base_url or "").strip(),
            model=(data.model or "").strip(),
            api_key_encrypted=_encrypt(key),
            timeout=data.timeout,
            max_concurrency=data.max_concurrency,
            enabled=data.enabled,
            is_default=False,
            updated_by=user_id,
        )
        self.repo.add(row)
        make_default = bool(data.is_default) or self.repo.get_default() is None
        if make_default:
            row.is_default = True
            row.enabled = True
            self.repo.clear_default(exclude_id=row.id)
        self.db.commit()
        self.db.refresh(row)
        return self._to_response(row)

    def update(
        self, setting_id: int, data: LlmSettingUpdate, user_id: Optional[int] = None
    ) -> LlmSettingResponse:
        row = self.repo.get(setting_id)
        if not row:
            raise NotFoundException(f"LLM 配置不存在: {setting_id}")
        payload = data.model_dump(exclude_unset=True)

        if "api_key" in payload:
            key = payload.pop("api_key")
            if key is not None and str(key).strip():
                row.api_key_encrypted = _encrypt(str(key).strip())

        for k, v in payload.items():
            if k in {"name", "base_url", "model"} and isinstance(v, str):
                v = v.strip()
            setattr(row, k, v)

        # 默认项 & 启用状态的联动，保证状态无歧义（「设为默认」优先，应用即启用）
        if payload.get("is_default") is True:
            row.enabled = True
            self.repo.clear_default(exclude_id=row.id)
            row.is_default = True
        elif payload.get("is_default") is False and row.is_default:
            row.is_default = False
        elif payload.get("enabled") is False and row.is_default:
            # 停用当前默认配置 → 自动取消默认标记
            row.is_default = False

        row.updated_by = user_id
        self.db.commit()
        self.db.refresh(row)
        return self._to_response(row)

    def delete(self, setting_id: int) -> None:
        row = self.repo.get(setting_id)
        if not row:
            raise NotFoundException(f"LLM 配置不存在: {setting_id}")
        self.repo.delete(row)
        self.db.commit()

    def apply(self, setting_id: int, user_id: Optional[int] = None) -> LlmSettingResponse:
        """应用 / 设为默认：该条立即成为标注/本体等 LLM 任务的生效配置。"""
        row = self.repo.get(setting_id)
        if not row:
            raise NotFoundException(f"LLM 配置不存在: {setting_id}")
        key = ""
        try:
            key = _decrypt(row.api_key_encrypted or "")
        except Exception:
            key = ""
        if not key:
            raise BusinessException("该配置缺少 API Key，无法应用", code="LLM_KEY_MISSING")
        row.enabled = True
        row.is_default = True
        row.updated_by = user_id
        self.repo.clear_default(exclude_id=row.id)
        self.db.commit()
        self.db.refresh(row)
        return self._to_response(row)

    # ---------- 测试 ----------

    def _do_test(self, client: LLMClient) -> dict:
        if not client.is_configured():
            raise BusinessException("未配置 LLM（缺少 API Key / Model）", code="LLM_NOT_CONFIGURED")
        started = time.perf_counter()
        text = client.chat(
            [{"role": "user", "content": "只回复两个字符：OK"}],
            temperature=0,
            max_tokens=64,
        )
        latency_ms = int((time.perf_counter() - started) * 1000)
        return {"ok": True, "reply": (text or "").strip()[:80], "latency_ms": latency_ms}

    def test_saved(self, setting_id: int) -> dict:
        row = self.repo.get(setting_id)
        if not row:
            raise NotFoundException(f"LLM 配置不存在: {setting_id}")
        key = ""
        try:
            key = _decrypt(row.api_key_encrypted or "")
        except Exception:
            key = ""
        if not key:
            raise BusinessException("该配置缺少 API Key", code="LLM_KEY_MISSING")
        return self._do_test(
            _build_client(base_url=row.base_url, model=row.model, api_key=key, timeout=row.timeout)
        )

    def test_inline(self, data: LlmSettingTestRequest) -> dict:
        """测试尚未保存的表单配置（前端「保存前先测试」）。"""
        return self._do_test(
            _build_client(
                base_url=data.base_url, model=data.model, api_key=data.api_key, timeout=data.timeout
            )
        )

    @staticmethod
    def _default_name(model: str) -> str:
        return (model or "").strip() or "LLM 配置"
