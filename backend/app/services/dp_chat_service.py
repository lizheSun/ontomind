"""数据平台-Text2SQL 会话服务。

流程：
1. `create_session` — 建 chat 会话。
2. `send_message` — 存用户消息 → 组装系统 prompt（含 schema summary）→
   调 LLMConfigService.chat_completion → 解析 fenced SQL → 存 assistant 消息。
3. `apply_message` — 拿 assistant 消息里的 generated_sql，走 DpQueryService.execute_sync
   过守卫再执行。executed=True 标记。

LLM 输出走守卫 = 用户输入走守卫 —— 同一个 sql_guard.validate_and_shape 函数。
"""
from __future__ import annotations

import re
from typing import Optional

from loguru import logger
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessException, NotFoundException
from app.db.repositories.dp_chat_repo import (
    DpChatMessageRepository,
    DpChatSessionRepository,
)
from app.schemas.dp_chat_schema import (
    MessageRead,
    SessionCreate,
    SessionRead,
    SessionUpdate,
)
from app.schemas.dp_query_schema import SqlExecuteResponse
from app.services.dp_data_source_service import DpDataSourceService
from app.services.dp_query_service import DpQueryService
from app.services.llm_config_service import LLMConfigService


_SQL_FENCE = re.compile(r"```(?:sql)?\s*\n?(.*?)\n?```", re.DOTALL | re.IGNORECASE)


class DpChatService:
    """Text-to-SQL 会话服务。"""

    def __init__(
        self,
        db: Session,
        *,
        ds_service: Optional[DpDataSourceService] = None,
        query_service: Optional[DpQueryService] = None,
        llm_service=None,  # duck-typed: needs async chat_completion(messages, config_id, temperature, max_tokens)
    ) -> None:
        self.db = db
        self.session_repo = DpChatSessionRepository(db)
        self.message_repo = DpChatMessageRepository(db)
        self.ds_service = ds_service or DpDataSourceService(db)
        self.query_service = query_service or DpQueryService(db, ds_service=self.ds_service)
        self.llm_service = llm_service or LLMConfigService(db)

    # ---- sessions ----------------------------------------------------

    def create_session(self, payload: SessionCreate, user_id: int) -> SessionRead:
        self._reset_autobegin()
        with self.db.begin():
            row = self.session_repo.create({**payload.model_dump(), "user_id": user_id})
        return SessionRead.model_validate(row)

    def list_sessions(self, user_id: int) -> list[SessionRead]:
        rows = self.session_repo.list_by_owner(user_id=user_id)
        return [SessionRead.model_validate(r) for r in rows]

    def get_session(self, id: int, user_id: int) -> SessionRead:
        row = self._require_owned_session(id, user_id)
        return SessionRead.model_validate(row)

    def update_session(self, id: int, payload: SessionUpdate, user_id: int) -> SessionRead:
        self._require_owned_session(id, user_id)
        self._reset_autobegin()
        with self.db.begin():
            self.session_repo.update(id, payload.model_dump(exclude_unset=True))
        return self.get_session(id, user_id)

    def delete_session(self, id: int, user_id: int) -> None:
        self._require_owned_session(id, user_id)
        self._reset_autobegin()
        with self.db.begin():
            self.session_repo.delete(id)

    def list_messages(self, session_id: int, user_id: int) -> list[MessageRead]:
        self._require_owned_session(session_id, user_id)
        rows = self.message_repo.list_by_session(session_id)
        return [MessageRead.model_validate(r) for r in rows]

    # ---- send / apply -----------------------------------------------

    async def send_message(
        self, *, session_id: int, content: str, user_id: int,
    ) -> MessageRead:
        session = self._require_owned_session(session_id, user_id)

        # 1. Persist user message
        self._reset_autobegin()
        with self.db.begin():
            self.message_repo.append(
                session_id=session_id, role="user", content=content,
            )

        # 2. Schema summary (best-effort)
        try:
            schema = self.ds_service.describe_schema(session.source_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"[dp-chat] describe_schema failed: {exc}")
            schema = {"databases": []}
        schema_summary = _summarize_schema(schema, max_tables=30)

        # 3. Get datasource dialect for prompt
        ds_row = self.ds_service.repo.get_by_id(session.source_id)
        dialect_zh = _dialect_display(ds_row.dialect if ds_row else "mysql")

        # 4. Call LLM
        messages = [
            {"role": "system", "content": _system_prompt(dialect_zh, schema_summary)},
            {"role": "user", "content": content},
        ]
        try:
            reply = await self.llm_service.chat_completion(
                messages=messages,
                config_id=session.model_config_id,
                temperature=0.1,
                max_tokens=800,
            )
        except Exception as exc:  # noqa: BLE001
            raise BusinessException(
                message=f"LLM 调用失败：{exc}"[:512],
                code="DP_CHAT_LLM_ERROR",
                status_code=502,
            ) from exc

        assistant_text = _extract_assistant_text(reply)
        generated_sql = _extract_sql_fence(assistant_text)

        # 5. Persist assistant message
        self._reset_autobegin()
        with self.db.begin():
            row = self.message_repo.append(
                session_id=session_id, role="assistant",
                content=assistant_text, generated_sql=generated_sql,
            )
        return MessageRead.model_validate(row)

    async def apply_message(
        self, *, session_id: int, message_id: int, user_id: int, max_rows: int = 1000,
    ) -> SqlExecuteResponse:
        session = self._require_owned_session(session_id, user_id)
        msg = self.message_repo.get_by_id(message_id)
        if msg is None or msg.session_id != session_id:
            raise NotFoundException(
                f"消息 id={message_id} 不存在",
                "DP_CHAT_MSG_NOT_FOUND",
            )
        if msg.role != "assistant" or not msg.generated_sql:
            raise BusinessException(
                message="该消息未包含可执行 SQL",
                code="DP_CHAT_NO_SQL",
                status_code=400,
            )

        # Same guard path as user-typed SQL
        resp = await self.query_service.execute_sync(
            source_id=session.source_id, sql=msg.generated_sql,
            max_rows=max_rows, user_id=user_id,
        )

        # Mark executed
        self._reset_autobegin()
        with self.db.begin():
            self.message_repo.mark_executed(message_id)
        return resp

    # ---- helpers ----------------------------------------------------

    def _reset_autobegin(self) -> None:
        if self.db.in_transaction():
            self.db.rollback()

    def _require_owned_session(self, id: int, user_id: int):
        row = self.session_repo.get_by_id(id)
        if row is None:
            raise NotFoundException(
                f"会话 id={id} 不存在",
                "DP_CHAT_SESSION_NOT_FOUND",
            )
        if row.user_id != user_id:
            raise BusinessException(
                message="仅会话创建者可操作",
                code="DP_CHAT_FORBIDDEN",
                status_code=403,
            )
        return row


# ==== helpers ======================================================

def _extract_assistant_text(reply) -> str:
    """兼容 dict / OpenAI-style / plain str / LLMConfigService normalized shape."""
    if isinstance(reply, str):
        return reply
    if isinstance(reply, dict):
        # OpenAI-compat: {"choices":[{"message":{"content":"..."}}]}
        try:
            return reply["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError):
            pass
        # LLMConfigService normalized: {"content": "...", "model": ..., "usage": ...}
        for k in ("content", "text", "message"):
            if k in reply and isinstance(reply[k], str):
                return reply[k]
    return str(reply)


def _extract_sql_fence(text: str) -> Optional[str]:
    if not text:
        return None
    m = _SQL_FENCE.search(text)
    if m:
        stripped = m.group(1).strip()
        return stripped or None
    # Unfenced fallback: whole thing is SQL?
    stripped = text.strip()
    if stripped.upper().startswith(("SELECT", "WITH")):
        return stripped
    return None


def _summarize_schema(schema: dict, *, max_tables: int) -> str:
    lines: list[str] = []
    for db_ in schema.get("databases", []):
        for tbl in db_.get("tables", [])[:max_tables]:
            cols = ", ".join(
                f"{c['name']} {c.get('type', 'UNKNOWN')}" for c in tbl["columns"]
            )
            lines.append(f"TABLE {tbl['name']} ({cols});")
    return "\n".join(lines) if lines else "(schema 不可用)"


def _dialect_display(dialect: str) -> str:
    return {
        "mysql": "MySQL", "mysql_readonly": "MySQL",
        "postgresql": "PostgreSQL", "sqlite": "SQLite",
    }.get(dialect, dialect)


def _system_prompt(dialect: str, schema_summary: str) -> str:
    return (
        f"你是一位精通 {dialect} 的数据库专家。用户会用中文提问，"
        f"你需要基于以下表结构生成一条语法正确、可直接执行的 {dialect} SELECT SQL。\n\n"
        f"# 表结构\n{schema_summary}\n\n"
        "# 输出规范（严格遵守）\n"
        "1. 只输出**一条** SELECT 语句，禁止 INSERT/UPDATE/DELETE/DROP/ALTER。\n"
        "2. 用 ```sql ...``` 代码块包裹 SQL，不要任何解释文字。\n"
        "3. 未指定聚合、排序时，必须显式添加 LIMIT 1000。\n"
        "4. 若无法回答，只输出一行：`-- CANNOT_ANSWER: <说明>`。\n"
        "5. 表名、列名严格来自上文，不得臆造。"
    )
