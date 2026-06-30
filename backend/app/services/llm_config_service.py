"""LLM 配置业务服务."""
import json
from typing import Optional
import httpx
from sqlalchemy.orm import Session
from app.db.repositories.llm_config_repo import LLMConfigRepository
from app.schemas.llm_config_schema import LLMConfigCreate, LLMConfigUpdate
from app.core.exceptions import ConflictException, NotFoundException


class LLMConfigService:
    """LLM 配置管理服务"""

    def __init__(self, db: Session):
        self.db = db
        self.repo = LLMConfigRepository(db)

    def create_config(self, data: LLMConfigCreate) -> dict:
        with self.db.begin():
            if self.repo.name_exists(data.name):
                raise ConflictException("配置名称已存在", code="LLM_CONFIG_NAME_EXISTS")

            config_dict = data.model_dump()

            # 如果设为激活，先停用其他
            if config_dict.get("is_active"):
                self.repo.deactivate_all()

            cfg = self.repo.create(config_dict)
            return cfg.to_response_dict()

    def get_config(self, config_id: int) -> dict:
        cfg = self.repo.get_by_id(config_id)
        if not cfg:
            raise NotFoundException(f"LLM 配置不存在: {config_id}")
        return cfg.to_response_dict()

    def list_configs(self, skip: int = 0, limit: int = 100) -> list[dict]:
        configs = self.repo.get_all(skip, limit)
        return [c.to_response_dict() for c in configs]

    def update_config(self, config_id: int, data: LLMConfigUpdate) -> dict:
        with self.db.begin():
            cfg = self.repo.get_by_id(config_id)
            if not cfg:
                raise NotFoundException(f"LLM 配置不存在: {config_id}")

            update_data = data.model_dump(exclude_unset=True)

            # 名称唯一性检查
            if "name" in update_data and update_data["name"] != cfg.name:
                if self.repo.name_exists(update_data["name"], exclude_id=config_id):
                    raise ConflictException("配置名称已存在", code="LLM_CONFIG_NAME_EXISTS")

            # 如果设为激活，先停用其他
            if update_data.get("is_active"):
                self.repo.deactivate_all()

            updated = self.repo.update(config_id, update_data)
            return updated.to_response_dict()

    def delete_config(self, config_id: int) -> bool:
        with self.db.begin():
            if not self.repo.delete(config_id):
                raise NotFoundException(f"LLM 配置不存在: {config_id}")
            return True

    def get_active_config(self) -> dict:
        cfg = self.repo.get_active()
        if not cfg:
            raise NotFoundException("没有激活的 LLM 配置，请先创建并激活一个配置")
        return cfg.to_response_dict()

    def get_config_for_call(self, config_id: Optional[int] = None) -> dict:
        """获取用于调用的配置（指定 ID 或默认激活）"""
        if config_id:
            return self.get_config(config_id)
        return self.get_active_config()

    async def chat_completion(
        self,
        messages: list[dict],
        config_id: Optional[int] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> dict:
        """调用 LLM 进行对话补全"""
        config = self.get_config_for_call(config_id)
        provider = config["provider"]
        base_url = config["base_url"].strip().rstrip("/")
        api_key = config["api_key"]
        model = config["model_name"]

        extra_headers = {}
        if config.get("extra_headers"):
            try:
                extra_headers = json.loads(config["extra_headers"])
            except json.JSONDecodeError:
                pass

        extra_body = {}
        if config.get("extra_body"):
            try:
                extra_body = json.loads(config["extra_body"])
            except json.JSONDecodeError:
                pass

        timeout = int(config.get("timeout", 60))
        max_retries = int(config.get("max_retries", 2))

        if provider == "openai" or provider == "qwen":
            return await self._call_openai(
                base_url, api_key, model, messages, temperature, max_tokens,
                extra_headers, extra_body, timeout, max_retries,
            )
        elif provider == "anthropic":
            return await self._call_anthropic(
                base_url, api_key, model, messages, temperature, max_tokens,
                extra_headers, extra_body, timeout, max_retries,
            )
        else:
            raise ValueError(f"不支持的 provider: {provider}")

    async def _call_openai(
        self, base_url, api_key, model, messages, temperature, max_tokens,
        extra_headers, extra_body, timeout, max_retries,
    ) -> dict:
        """调用 OpenAI 兼容协议"""
        url = f"{base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            **extra_headers,
        }
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            **extra_body,
        }

        last_error = None
        async with httpx.AsyncClient(timeout=timeout) as client:
            for attempt in range(max_retries + 1):
                try:
                    resp = await client.post(url, json=payload, headers=headers)
                    resp.raise_for_status()
                    data = resp.json()
                    choice = data["choices"][0]
                    msg = choice["message"]
                    content = msg.get("content")
                    # 部分模型（如 Qwen 推理模型）可能 content 为 null，实际内容在 reasoning 字段
                    if not content:
                        content = msg.get("reasoning") or msg.get("reasoning_content") or ""
                    return {
                        "content": content,
                        "model": data.get("model", model),
                        "usage": data.get("usage"),
                    }
                except httpx.HTTPStatusError as e:
                    # 4xx 客户端错误不重试
                    if 400 <= e.response.status_code < 500:
                        raise RuntimeError(f"OpenAI API 错误 {e.response.status_code}: {e.response.text}")
                    last_error = e
                except httpx.RequestError as e:
                    last_error = e
        raise RuntimeError(f"请求 OpenAI 失败: {str(last_error)}")

    async def _call_anthropic(
        self, base_url, api_key, model, messages, temperature, max_tokens,
        extra_headers, extra_body, timeout, max_retries,
    ) -> dict:
        """调用 Anthropic 兼容协议"""
        url = f"{base_url}/messages"
        headers = {
            "x-api-key": api_key,
            "anthropic-version": extra_headers.pop("anthropic-version", "2023-06-01"),
            "Content-Type": "application/json",
            **extra_headers,
        }

        # Anthropic 系统消息是独立字段
        system_msgs = [m["content"] for m in messages if m["role"] == "system"]
        chat_msgs = [m for m in messages if m["role"] != "system"]

        payload = {
            "model": model,
            "messages": chat_msgs,
            "max_tokens": max_tokens,
            "temperature": temperature,
            **extra_body,
        }
        if system_msgs:
            payload["system"] = "\n".join(system_msgs)

        last_error = None
        async with httpx.AsyncClient(timeout=timeout) as client:
            for attempt in range(max_retries + 1):
                try:
                    resp = await client.post(url, json=payload, headers=headers)
                    resp.raise_for_status()
                    data = resp.json()
                    content_blocks = data.get("content", [])
                    text = "\n".join(
                        b.get("text", "") for b in content_blocks if b.get("type") == "text"
                    )
                    return {
                        "content": text,
                        "model": data.get("model", model),
                        "usage": data.get("usage"),
                    }
                except httpx.HTTPStatusError as e:
                    # 4xx 客户端错误不重试
                    if 400 <= e.response.status_code < 500:
                        raise RuntimeError(f"Anthropic API 错误 {e.response.status_code}: {e.response.text}")
                    last_error = e
                except httpx.RequestError as e:
                    last_error = e
        raise RuntimeError(f"请求 Anthropic 失败: {str(last_error)}")
