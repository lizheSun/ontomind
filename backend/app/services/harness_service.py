"""统一会话服务：会话 CRUD + 把插件 StreamEvent 写成消息 parts。"""
from __future__ import annotations

import asyncio
import re
from pathlib import Path
from typing import Any, AsyncIterator, Optional

from sqlalchemy.orm import Session

from app.core.exceptions import BusinessException, NotFoundException
from app.db.models.harness_model import HarnessMessage, HarnessSession
from app.db.repositories.harness_repo import HarnessRepository
from app.harness.protocol import RunRequest, StreamEvent
from app.harness.registry import get_registry
from app.schemas.harness_schema import SessionCreate, SessionUpdate
from app.services.llm_settings_service import resolve_llm_client

_MAX_UPLOAD = 12 * 1024 * 1024
_SAFE_NAME = re.compile(r"[^A-Za-z0-9._+\-()\u4e00-\u9fff]+")
_PLACEHOLDER_TITLES = {"", "新会话", "新任务"}


def workspace_dir(user_id: int, session_id: int) -> Path:
    path = Path.home() / ".ontomind" / "harness" / f"u{user_id}" / f"s{session_id}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def resolve_workspace(raw: str, *, must_exist: bool = True) -> Path:
    text = (raw or "").strip()
    if not text or "\x00" in text:
        raise BusinessException("工作区路径无效", code="BAD_WORKSPACE")
    path = Path(text).expanduser()
    if not path.is_absolute():
        raise BusinessException("工作区必须是绝对路径", code="BAD_WORKSPACE")
    path = path.resolve()
    if must_exist and not path.is_dir():
        raise BusinessException("工作区目录不存在", code="BAD_WORKSPACE")
    return path


def safe_filename(name: str) -> str:
    base = Path(name or "").name.strip() or "file"
    cleaned = _SAFE_NAME.sub("_", base).strip("._") or "file"
    return cleaned[:180]


def compose_plugin_prompt(content: str, attachments: list[str]) -> str:
    files = [a.strip() for a in attachments if a and a.strip()]
    if not files:
        return content
    listing = "\n".join(f"- {p}" for p in files)
    return f"工作区里已放入这些文件，请结合它们处理：\n{listing}\n\n{content}"


def apply_event(parts: list[dict[str, Any]], ev: StreamEvent) -> None:
    if ev.kind in ("status", "meta"):
        return
    if ev.part_id:
        for p in parts:
            if p.get("part_id") == ev.part_id:
                _merge_part(p, ev)
                return
        parts.append(_new_part(ev))
        return
    if ev.kind in ("text", "thinking"):
        if ev.delta and parts and parts[-1].get("kind") == ev.kind:
            parts[-1]["text"] = str(parts[-1].get("text") or "") + ev.text
        else:
            parts.append(_new_part(ev))
        return
    if ev.kind == "execute":
        for p in parts:
            if p.get("kind") == "execute" and ev.tool_id and p.get("tool_id") == ev.tool_id:
                _merge_part(p, ev)
                return
        parts.append(_new_part(ev))
        return
    if ev.kind == "error":
        parts.append(_new_part(ev))


def _new_part(ev: StreamEvent) -> dict[str, Any]:
    row: dict[str, Any] = {"kind": ev.kind}
    if ev.part_id:
        row["part_id"] = ev.part_id
    if ev.kind in ("text", "thinking", "error"):
        row["text"] = ev.text
    if ev.kind == "execute":
        row["tool_id"] = ev.tool_id
        row["tool_name"] = ev.tool_name
        row["tool_status"] = ev.tool_status or "running"
        row["summary"] = ev.summary
        row["output"] = ev.output
    return row


def _merge_part(p: dict[str, Any], ev: StreamEvent) -> None:
    if ev.kind in ("text", "thinking"):
        if ev.delta:
            p["text"] = str(p.get("text") or "") + ev.text
        elif ev.text or not ev.delta:
            p["text"] = ev.text
        return
    if ev.kind == "execute":
        if ev.tool_name:
            p["tool_name"] = ev.tool_name
        if ev.tool_status:
            p["tool_status"] = ev.tool_status
        if ev.summary:
            p["summary"] = ev.summary
        if ev.output:
            p["output"] = ev.output
        if ev.text and not ev.output:
            p["output"] = ev.text


def _strip_chat_url(url: str) -> str:
    u = (url or "").rstrip("/")
    for suffix in ("/chat/completions", "/v1"):
        if u.endswith(suffix):
            u = u[: -len(suffix)]
    return u


class HarnessService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = HarnessRepository(db)

    def list_plugins(self) -> list[dict[str, Any]]:
        return [p.to_dict() for p in get_registry().list_info()]

    def list_sessions(self, user_id: int) -> list[dict[str, Any]]:
        return [self._session_resp(s) for s in self.repo.list_sessions(user_id)]

    def create_session(self, user_id: int, data: SessionCreate) -> dict[str, Any]:
        plugin = get_registry().get(data.plugin_id)
        if plugin is None:
            raise BusinessException("未知插件", code="UNKNOWN_PLUGIN")
        row = HarnessSession(
            user_id=user_id,
            title=(data.title or "").strip() or "新会话",
            plugin_id=data.plugin_id,
            workspace_path="",
        )
        self.repo.add_session(row)
        self.db.flush()
        if data.workspace_path:
            row.workspace_path = str(resolve_workspace(data.workspace_path))
        else:
            row.workspace_path = str(workspace_dir(user_id, row.id))
        self.db.commit()
        self.db.refresh(row)
        return self._session_resp(row)

    def get_session(self, user_id: int, session_id: int) -> dict[str, Any]:
        return self._session_resp(self._owned(user_id, session_id))

    def update_session(self, user_id: int, session_id: int, data: SessionUpdate) -> dict[str, Any]:
        row = self._owned(user_id, session_id)
        payload = data.model_dump(exclude_unset=True)
        if "plugin_id" in payload and get_registry().get(payload["plugin_id"]) is None:
            raise BusinessException("未知插件", code="UNKNOWN_PLUGIN")
        if "workspace_path" in payload:
            payload["workspace_path"] = str(resolve_workspace(payload["workspace_path"]))
        for k, v in payload.items():
            setattr(row, k, v)
        self.db.commit()
        self.db.refresh(row)
        return self._session_resp(row)

    def delete_session(self, user_id: int, session_id: int) -> None:
        row = self._owned(user_id, session_id)
        self.repo.delete_session(row)
        self.db.commit()

    def list_messages(self, user_id: int, session_id: int) -> list[dict[str, Any]]:
        self._owned(user_id, session_id)
        return [self._msg_resp(m) for m in self.repo.list_messages(session_id)]

    def list_workspaces(self, user_id: int) -> dict[str, Any]:
        home = str(Path.home())
        recents: list[dict[str, str]] = []
        seen = {home}
        for row in self.repo.list_sessions(user_id):
            raw = (row.workspace_path or "").strip()
            if not raw or raw in seen:
                continue
            if "/.ontomind/harness/" in raw or "\\.ontomind\\harness\\" in raw:
                continue
            path = Path(raw)
            if not path.is_dir():
                continue
            recents.append({"path": raw, "label": path.name or raw, "kind": "recent"})
            seen.add(raw)
            if len(recents) >= 8:
                break
        return {"home": home, "recents": recents}

    def save_uploads(self, user_id: int, session_id: int, files: list[tuple[str, bytes]]) -> list[dict[str, Any]]:
        sess = self._owned(user_id, session_id)
        ws = Path(sess.workspace_path) if sess.workspace_path else workspace_dir(user_id, sess.id)
        ws.mkdir(parents=True, exist_ok=True)
        inbox = ws / "inbox"
        inbox.mkdir(parents=True, exist_ok=True)
        out: list[dict[str, Any]] = []
        for original, data in files:
            if len(data) > _MAX_UPLOAD:
                raise BusinessException("单个文件不能超过 12MB", code="FILE_TOO_LARGE")
            name = safe_filename(original)
            dest = inbox / name
            n = 1
            while dest.exists():
                dest = inbox / f"{dest.stem}_{n}{dest.suffix}"
                n += 1
            dest.write_bytes(data)
            rel = str(Path("inbox") / dest.name)
            out.append({"name": dest.name, "rel": rel, "size": len(data)})
        return out

    def optimize_prompt(self, text: str, plugin_id: Optional[str] = None) -> str:
        client = resolve_llm_client(self.db)
        agent = "OpenCode 编码助手" if plugin_id == "opencode" else "通用 AI 助手"
        rewritten = client.chat(
            [
                {
                    "role": "system",
                    "content": (
                        f"你把用户的草稿改写成给{agent}的清晰提示。"
                        "保留原意和约束，补全缺失的目标、输入和期望输出。"
                        "只输出改写后的提示，不要解释，不要加引号。"
                    ),
                },
                {"role": "user", "content": text.strip()},
            ],
            temperature=0.3,
            max_tokens=1200,
        )
        cleaned = rewritten.strip().strip("\"'")
        if not cleaned:
            raise BusinessException("优化结果为空", code="OPTIMIZE_EMPTY")
        return cleaned

    async def stream_message(
        self,
        *,
        user_id: int,
        session_id: int,
        content: str,
        plugin_id: Optional[str] = None,
        attachments: Optional[list[str]] = None,
        cancel: Optional[asyncio.Event] = None,
    ) -> AsyncIterator[StreamEvent]:
        sess = self._owned(user_id, session_id)
        pid = plugin_id or sess.plugin_id
        plugin = get_registry().get(pid)
        if plugin is None:
            raise BusinessException("未知插件", code="UNKNOWN_PLUGIN")
        if sess.plugin_id != pid:
            sess.plugin_id = pid
            sess.plugin_session_id = None

        files = [a.strip() for a in (attachments or []) if a and a.strip()]
        user_parts: list[dict[str, Any]] = [{"kind": "text", "text": content}]
        for rel in files:
            user_parts.append({"kind": "file", "name": Path(rel).name, "text": rel})
        user_row = HarnessMessage(
            session_id=sess.id,
            role="user",
            parts_json=user_parts,
        )
        self.repo.add_message(user_row)
        if (sess.title or "").strip() in _PLACEHOLDER_TITLES:
            head = content.strip().splitlines()[0].strip()
            sess.title = (head[:40] if head else sess.title or "新会话")
        asst = HarnessMessage(session_id=sess.id, role="assistant", parts_json=[])
        self.repo.add_message(asst)
        self.db.commit()
        self.db.refresh(asst)
        from app.services.kanban_sync import sync_session_run_status

        sync_session_run_status(self.db, sess.id, "running", title=sess.title)
        self.db.commit()
        yield StreamEvent(kind="meta", delta=False, meta={"message_id": asst.id, "user_message_id": user_row.id})

        ws = Path(sess.workspace_path) if sess.workspace_path else workspace_dir(user_id, sess.id)
        env, model = self._runner_env(pid)
        req = RunRequest(
            session_key=f"om-{sess.id}",
            workspace=ws,
            prompt=compose_plugin_prompt(content, files),
            plugin_session_id=sess.plugin_session_id,
            env=env,
            model=model,
            cancel=cancel,
        )
        parts: list[dict[str, Any]] = []
        last: StreamEvent | None = None
        try:
            async for ev in plugin.stream(req):
                last = ev
                if cancel is not None and cancel.is_set():
                    break
                if ev.kind == "meta" and ev.meta.get("plugin_session_id"):
                    sess.plugin_session_id = str(ev.meta["plugin_session_id"])
                apply_event(parts, ev)
                yield ev
            asst.parts_json = list(parts)
            if last is not None and last.kind == "error":
                asst.error_text = last.text
        except Exception as exc:  # noqa: BLE001 — 插件子进程失败要回给前端
            err = StreamEvent(kind="error", text=str(exc), delta=False)
            apply_event(parts, err)
            asst.error_text = str(exc)
            yield err
        finally:
            asst.parts_json = list(parts)
            cancelled = cancel is not None and cancel.is_set()
            if asst.error_text:
                run_status = "failed"
            elif cancelled:
                run_status = "waiting"
            else:
                run_status = "completed"
            from app.services.kanban_sync import sync_session_run_status

            texts = [str(p.get("text") or "") for p in parts if p.get("kind") == "text"]
            summary = " ".join(" ".join(texts).split())[:180] or None
            sync_session_run_status(
                self.db,
                sess.id,
                run_status,
                title=sess.title,
                summary=summary,
            )
            self.db.commit()

    def _runner_env(self, plugin_id: str) -> tuple[dict[str, str], str]:
        if plugin_id != "dsh":
            return {}, ""
        client = resolve_llm_client(self.db)
        env: dict[str, str] = {}
        if client.api_key:
            env["DEEPSEEK_API_KEY"] = client.api_key
        url = _strip_chat_url(client.base_url)
        if url:
            env["DEEPSEEK_BASE_URL"] = url
        from app.harness.plugins.dsh import resolve_dsh_model

        model = resolve_dsh_model(client.model or "")
        env["DEEPSEEK_MODEL"] = model
        return env, model

    def _owned(self, user_id: int, session_id: int) -> HarnessSession:
        row = self.repo.get_session(session_id)
        if row is None or row.user_id != user_id:
            raise NotFoundException("会话不存在")
        return row

    def _session_resp(self, row: HarnessSession) -> dict[str, Any]:
        return {
            "id": row.id,
            "title": row.title,
            "plugin_id": row.plugin_id,
            "plugin_session_id": row.plugin_session_id,
            "workspace_path": row.workspace_path or "",
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }

    def _msg_resp(self, row: HarnessMessage) -> dict[str, Any]:
        parts = row.parts_json if isinstance(row.parts_json, list) else []
        return {
            "id": row.id,
            "session_id": row.session_id,
            "role": row.role,
            "parts": parts,
            "error_text": row.error_text,
            "created_at": row.created_at,
        }
