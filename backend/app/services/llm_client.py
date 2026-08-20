"""OpenAI 兼容 /chat/completions 客户端（仅 httpx）。"""
from __future__ import annotations

import json
import re
from typing import Any, Optional

import httpx

from app.core.config import settings
from app.core.exceptions import BusinessException

_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)


def _strip_json_fence(text: str) -> str:
    raw = (text or "").strip()
    if not raw:
        return raw
    m = _FENCE_RE.search(raw)
    if m:
        return m.group(1).strip()
    return raw


class LLMClient:
    def __init__(
        self,
        *,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> None:
        self.base_url = (base_url or settings.LLM_BASE_URL or "").rstrip("/")
        self.api_key = api_key if api_key is not None else (settings.LLM_API_KEY or "")
        self.model = model or settings.LLM_MODEL or ""
        self.timeout = int(timeout if timeout is not None else settings.LLM_TIMEOUT or 120)

    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    def _require_configured(self) -> None:
        if not self.is_configured():
            raise BusinessException(
                "未配置 LLM，请在 GovOps → LLM 配置 或 .env 设置 LLM_API_KEY",
                code="LLM_NOT_CONFIGURED",
            )
        if not self.model:
            raise BusinessException(
                "未配置 LLM_MODEL",
                code="LLM_NOT_CONFIGURED",
            )

    def chat(
        self,
        messages: list[dict[str, Any]],
        *,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        response_format: Optional[dict[str, Any]] = None,
    ) -> str:
        self._require_configured()
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        body: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format is not None:
            body["response_format"] = response_format

        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(url, headers=headers, json=body)
                if (
                    response_format is not None
                    and resp.status_code in (400, 422)
                ):
                    body.pop("response_format", None)
                    resp = client.post(url, headers=headers, json=body)
                if resp.status_code >= 400:
                    raise BusinessException(
                        f"LLM 调用失败: HTTP {resp.status_code} {resp.text[:300]}",
                        code="LLM_HTTP_ERROR",
                    )
                data = resp.json()
        except BusinessException:
            raise
        except Exception as exc:
            raise BusinessException(f"LLM 调用失败: {exc}", code="LLM_HTTP_ERROR") from exc

        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise BusinessException("LLM 响应格式异常", code="LLM_BAD_RESPONSE") from exc
        return str(content or "")

    def chat_json(
        self,
        messages: list[dict[str, Any]],
        *,
        schema_hint: str,
        temperature: float = 0.1,
        max_retries: int = 2,
    ) -> dict[str, Any]:
        self._require_configured()
        system_extra = (
            "只输出 JSON，不要 markdown 代码块，不要解释文字。\n"
            f"JSON schema:\n{schema_hint}"
        )
        msgs = list(messages)
        if msgs and msgs[0].get("role") == "system":
            msgs[0] = {
                **msgs[0],
                "content": f"{msgs[0].get('content', '')}\n\n{system_extra}",
            }
        else:
            msgs = [{"role": "system", "content": system_extra}, *msgs]

        last_raw = ""
        for attempt in range(max_retries + 1):
            raw = self.chat(
                msgs,
                temperature=temperature,
                response_format={"type": "json_object"},
            )
            last_raw = raw
            try:
                parsed = json.loads(_strip_json_fence(raw))
                if isinstance(parsed, dict):
                    return parsed
                raise ValueError("root is not object")
            except Exception:
                if attempt >= max_retries:
                    break
                msgs = [
                    *msgs,
                    {"role": "assistant", "content": raw},
                    {
                        "role": "user",
                        "content": (
                            "上一次输出不是合法 JSON object，请严格按 schema 只输出修正后的 JSON。"
                        ),
                    },
                ]

        raise BusinessException(
            f"LLM 输出无法解析为 JSON: {last_raw[:400]}",
            code="LLM_INVALID_JSON",
        )
