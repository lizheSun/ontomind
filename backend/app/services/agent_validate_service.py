"""Agent / Skill / Bundle 校验器.

**为什么校验必须前置到设计态**：
OpenCode 对不认识的权限键是**静默忽略**的 —— 写错 `write: deny`（应为 `edit`）
不会报错，只会不生效。用户以为限制住了，实际 agent 有全部写权限。
这类问题在运行时几乎无法排查，所以必须在存入 DB 前就拦掉。

校验分两级：
- `error`   阻断保存/发布
- `warning` 仅提示（多为「这样写可能不是你想要的」）
"""
import re
from typing import Any, Dict, List, Optional, Sequence

from app.schemas.agent_factory_schema import (
    AGENT_NAME_PATTERN,
    GLOB_CAPABLE_KEYS,
    PERMISSION_ACTIONS,
    PERMISSION_KEYS,
    SKILL_NAME_PATTERN,
    ValidationIssue,
    ValidationResult,
)

# 常见误写 → 正确键的纠错映射，让报错能直接给出「你应该写什么」
COMMON_KEY_MISTAKES: Dict[str, str] = {
    "write": "edit",
    "apply_patch": "edit",
    "patch": "edit",
    "read_file": "read",
    "search": "grep",
    "find": "glob",
    "ls": "list",
    "shell": "bash",
    "command": "bash",
    "subagent": "task",
    "agent": "task",
    "todo": "todowrite",
    "web_search": "websearch",
    "web_fetch": "webfetch",
    "fetch": "webfetch",
    "skills": "skill",
}

_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
_THEME_COLORS = {
    "primary", "secondary", "accent", "success", "warning", "error", "info",
}
_ENV_KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _err(field: str, message: str) -> ValidationIssue:
    return ValidationIssue(level="error", field=field, message=message)


def _warn(field: str, message: str) -> ValidationIssue:
    return ValidationIssue(level="warning", field=field, message=message)


def _info(field: str, message: str) -> ValidationIssue:
    """纯说明：配置完全合法，只是把「会发生什么」讲清楚。"""
    return ValidationIssue(level="info", field=field, message=message)


# ---------------------------------------------------------------------------
# 权限校验
# ---------------------------------------------------------------------------

def validate_permission(
    permission: Optional[Dict[str, Any]], field_prefix: str = "permission"
) -> List[ValidationIssue]:
    """校验 permission 配置。这是整个校验器最重要的部分。"""
    issues: List[ValidationIssue] = []
    if not permission:
        return issues
    if not isinstance(permission, dict):
        return [_err(field_prefix, "permission 必须是对象，如 {\"edit\": \"deny\"}")]

    for key, value in permission.items():
        path = f"{field_prefix}.{key}"

        # ① 未知权限键 —— OpenCode 会静默忽略，必须拦
        if key not in PERMISSION_KEYS:
            hint = COMMON_KEY_MISTAKES.get(key)
            if hint:
                issues.append(_err(
                    path,
                    f"'{key}' 不是 OpenCode 的权限键，应该写 '{hint}'。"
                    f"（OpenCode 对未知键静默忽略，不会报错但也不生效）",
                ))
            else:
                issues.append(_err(
                    path,
                    f"'{key}' 不是合法权限键。合法键共 15 个："
                    f"{', '.join(PERMISSION_KEYS)}",
                ))
            continue

        # ② 简写动作
        if isinstance(value, str):
            if value not in PERMISSION_ACTIONS:
                issues.append(_err(
                    path,
                    f"动作 '{value}' 非法，只能是 allow / ask / deny",
                ))
            continue

        # ③ glob 映射
        if isinstance(value, dict):
            if key not in GLOB_CAPABLE_KEYS:
                issues.append(_err(
                    path,
                    f"'{key}' 不支持 glob 细粒度配置，只能给简写动作（allow/ask/deny）。"
                    f"支持 glob 的键是：{', '.join(GLOB_CAPABLE_KEYS)}",
                ))
                continue
            if not value:
                issues.append(_warn(path, "空的 glob 映射不会产生任何规则"))
                continue

            patterns = list(value.keys())
            for pat, act in value.items():
                if not isinstance(act, str) or act not in PERMISSION_ACTIONS:
                    issues.append(_err(
                        f"{path}.{pat}",
                        f"动作 '{act}' 非法，只能是 allow / ask / deny",
                    ))

            # ④ "*" 位置 —— OpenCode 是「最后匹配胜出」
            if "*" in patterns and patterns.index("*") != 0:
                later = patterns[patterns.index("*") + 1:]
                issues.append(_warn(
                    path,
                    f"OpenCode 按顺序匹配且**最后匹配的规则胜出**，"
                    f"'*' 写在中间会覆盖它后面的 {later}。"
                    f"请把 '*' 放到第一个。",
                ))
            continue

        issues.append(_err(
            path,
            f"值类型非法（{type(value).__name__}）。"
            f"应为动作字符串（如 \"deny\"）或 glob 映射（如 {{\"*\": \"ask\", \"git diff\": \"allow\"}}）",
        ))

    return issues


# ---------------------------------------------------------------------------
# Agent 校验
# ---------------------------------------------------------------------------

def validate_agent(data: Dict[str, Any]) -> ValidationResult:
    """校验单个 agent 模板。data 用 schema 的字段名（permission_json 等）。"""
    issues: List[ValidationIssue] = []

    name = (data.get("name") or "").strip()
    if not name:
        issues.append(_err("name", "agent 名不能为空"))
    elif not re.match(AGENT_NAME_PATTERN, name):
        issues.append(_err(
            "name",
            f"'{name}' 不合法。只能用小写字母、数字和单个连字符分隔，"
            f"不能以 '-' 开头/结尾，不能有连续 '--'。例：code-reviewer",
        ))
    elif len(name) > 64:
        issues.append(_err("name", "agent 名不能超过 64 字符"))

    desc = (data.get("description") or "").strip()
    if not desc:
        issues.append(_err(
            "description",
            "描述不能为空 —— primary agent 完全依据它判断何时委派这个 subagent，"
            "写得越具体委派越准确",
        ))
    elif len(desc) > 1024:
        issues.append(_err("description", f"描述 {len(desc)} 字符，超过 1024 上限"))
    elif len(desc) < 15:
        issues.append(_warn(
            "description",
            "描述过短，模型可能无法准确判断何时使用该 agent。"
            "建议写清「做什么 + 什么场景用」",
        ))

    mode = data.get("mode") or "all"
    if mode not in ("subagent", "primary", "all"):
        issues.append(_err("mode", f"mode '{mode}' 非法，只能是 subagent / primary / all"))

    # hidden 只对 subagent 有意义
    if data.get("hidden") and mode == "primary":
        issues.append(_warn(
            "hidden",
            "hidden 只影响 subagent 在 @ 补全里的可见性，对 primary 无效果",
        ))

    for f in ("temperature", "top_p"):
        v = data.get(f)
        if v is None:
            continue
        if f == "temperature" and not (0.0 <= v <= 2.0):
            issues.append(_warn(f, f"{f}={v} 超出常见范围 0.0–1.0"))
        if f == "top_p" and not (0.0 <= v <= 1.0):
            issues.append(_err(f, f"top_p={v} 必须在 0.0–1.0"))

    steps = data.get("steps")
    if steps is not None and steps < 1:
        issues.append(_err("steps", "steps 至少为 1"))
    if steps is not None and steps > 200:
        issues.append(_warn("steps", f"steps={steps} 偏大，可能带来较高成本"))

    color = data.get("color")
    if color and not (_COLOR_RE.match(color) or color in _THEME_COLORS):
        issues.append(_err(
            "color",
            f"'{color}' 非法。应为 #RRGGBB（如 #3b52af）或主题色："
            f"{', '.join(sorted(_THEME_COLORS))}",
        ))

    model = data.get("model")
    if model and "/" not in model:
        issues.append(_warn(
            "model",
            f"'{model}' 缺少 provider 前缀，OpenCode 期望 'provider/model-id' 格式，"
            f"如 anthropic/claude-sonnet-4-5",
        ))

    perm = data.get("permission_json") or data.get("permission")
    issues.extend(validate_permission(perm))

    # 高危组合提示
    if isinstance(perm, dict):
        def _is_allow(k: str) -> bool:
            v = perm.get(k)
            if v == "allow":
                return True
            if isinstance(v, dict) and v.get("*") == "allow":
                return True
            return False

        if _is_allow("edit") and _is_allow("bash"):
            issues.append(_warn(
                "permission",
                "edit 与 bash 同时 allow：该 agent 可无确认地改文件并执行任意命令。"
                "确认这是你想要的（建议至少把 bash 收成 ask 或按命令白名单）",
            ))
        if _is_allow("external_directory"):
            issues.append(_warn(
                "permission.external_directory",
                "允许访问工作区外目录，存在越界读写风险，建议改用 glob 限定具体路径",
            ))

    ok = not any(i.level == "error" for i in issues)
    return ValidationResult(ok=ok, issues=issues)


# ---------------------------------------------------------------------------
# Skill 校验
# ---------------------------------------------------------------------------

def validate_skill_files(files: Sequence[Dict[str, Any]]) -> List[ValidationIssue]:
    """校验 skill 附属文件路径 —— 防路径穿越，防与 SKILL.md 冲突。"""
    issues: List[ValidationIssue] = []
    seen: set = set()

    for idx, f in enumerate(files or []):
        rel = (f.get("rel_path") or "").strip()
        path = f"files[{idx}].rel_path"

        if not rel:
            issues.append(_err(path, "路径不能为空"))
            continue
        if rel.startswith("/") or (len(rel) > 1 and rel[1] == ":"):
            issues.append(_err(path, f"'{rel}' 不能是绝对路径，必须是相对 skill 目录的路径"))
            continue
        if ".." in rel.split("/"):
            issues.append(_err(path, f"'{rel}' 含 '..'，禁止路径穿越"))
            continue
        if rel.upper() == "SKILL.MD":
            issues.append(_err(
                path,
                "SKILL.md 由正文字段（body）生成，不要作为附属文件重复添加",
            ))
            continue
        if rel in seen:
            issues.append(_err(path, f"路径 '{rel}' 重复"))
            continue
        if len(rel) > 512:
            issues.append(_err(path, "路径过长（>512）"))
            continue
        seen.add(rel)

        content = f.get("content") or ""
        if len(content.encode("utf-8")) > 1024 * 1024:
            issues.append(_err(
                f"files[{idx}].content",
                f"'{rel}' 超过单文件 1MB 上限",
            ))

    total = sum(len((f.get("content") or "").encode("utf-8")) for f in (files or []))
    if total > 10 * 1024 * 1024:
        issues.append(_err("files", "附属文件总大小超过 10MB 上限"))

    return issues


def validate_skill(data: Dict[str, Any]) -> ValidationResult:
    """校验单个 skill 模板。"""
    issues: List[ValidationIssue] = []

    name = (data.get("name") or "").strip()
    if not name:
        issues.append(_err("name", "skill 名不能为空"))
    elif not re.match(SKILL_NAME_PATTERN, name):
        issues.append(_err(
            "name",
            f"'{name}' 不合法。OpenCode 要求：1–64 字符、小写字母数字与单连字符、"
            f"不以 '-' 开头结尾、无连续 '--'。例：git-release",
        ))
    elif len(name) > 64:
        issues.append(_err("name", "skill 名不能超过 64 字符"))

    desc = (data.get("description") or "").strip()
    if not desc:
        issues.append(_err(
            "description",
            "描述不能为空 —— 这是模型判断「何时加载该 skill」的唯一依据",
        ))
    elif len(desc) > 1024:
        issues.append(_err(
            "description",
            f"描述 {len(desc)} 字符，超过 OpenCode 的 1024 上限",
        ))
    elif len(desc) < 20:
        issues.append(_warn(
            "description",
            "描述过短。建议写清「我做什么 + 什么场景触发我」，否则模型可能不会加载它",
        ))

    md = data.get("metadata_json")
    if md is not None:
        if not isinstance(md, dict):
            issues.append(_err("metadata_json", "metadata 必须是对象"))
        else:
            for k, v in md.items():
                if not isinstance(v, str):
                    issues.append(_err(
                        f"metadata_json.{k}",
                        f"metadata 的值必须是字符串（当前 {type(v).__name__}）—— "
                        f"OpenCode 只接受 string→string 映射",
                    ))

    body = data.get("body") or ""
    if not body.strip():
        issues.append(_warn("body", "正文为空，模型加载后拿不到任何指导内容"))

    files = data.get("files") or []
    issues.extend(validate_skill_files(files))

    # 渐进披露建议：正文过长时提示下沉
    body_lines = body.count("\n") + 1 if body else 0
    if body_lines > 400 and not files:
        issues.append(_warn(
            "body",
            f"正文约 {body_lines} 行且没有附属文件。SKILL.md 会常驻上下文，"
            f"建议把低频细节下沉到 references/*.md，正文里用链接指引（渐进披露）",
        ))

    ok = not any(i.level == "error" for i in issues)
    return ValidationResult(ok=ok, issues=issues)


# ---------------------------------------------------------------------------
# Bundle 校验（拓扑一致性 —— Loop 能不能真正跑起来）
# ---------------------------------------------------------------------------

def validate_bundle(
    bundle: Dict[str, Any],
    agents: Sequence[Dict[str, Any]],
    skills: Sequence[Dict[str, Any]],
) -> ValidationResult:
    """校验编排方案。

    Args:
        bundle: bundle 字段（name/pattern/default_agent/subagent_depth/...）
        agents: 成员 agent 的完整定义列表（含 name/mode/permission_json）
        skills: 成员 skill 定义列表（含 name）
    """
    issues: List[ValidationIssue] = []

    if not (bundle.get("name") or "").strip():
        issues.append(_err("name", "方案名不能为空"))

    agent_names = {a.get("name") for a in agents if a.get("name")}
    primaries = [a for a in agents if a.get("mode") in ("primary", "all")]
    subagents = [a for a in agents if a.get("mode") in ("subagent", "all")]

    # OpenCode 自带的 primary，永远存在，可直接作为对话入口
    BUILTIN_PRIMARY = {"build", "plan"}
    da = bundle.get("default_agent")
    # 依赖内置 primary 是**完全合法**的用法：
    # 例如「先规划后执行」方案只自定义 subagent，主对话直接用内置 plan/build。
    relies_on_builtin = (da in BUILTIN_PRIMARY) if da else False

    # ① 必须有能对话的入口：自定义 primary 或 内置 build/plan
    if not primaries and not relies_on_builtin:
        issues.append(_err(
            "members",
            "方案里没有可对话的入口。二选一："
            "① 把某个 agent 成员的角色设为「主对话」(primary)；"
            "② 把「默认入口 agent」设为 OpenCode 内置的 build 或 plan。",
        ))
    elif not primaries and relies_on_builtin:
        # 合法，但明确告知用户主对话来自内置 agent（而非本方案定义）
        issues.append(_info(
            "members",
            f"本方案未自定义 primary，主对话将使用 OpenCode 内置的 '{da}'。"
            f"方案里的 subagent 由它按 description 自动委派或用 @ 手动召唤。",
        ))

    # ② default_agent 必须是 primary
    if da:
        if da in agent_names:
            hit = next(a for a in agents if a.get("name") == da)
            if hit.get("mode") == "subagent":
                issues.append(_err(
                    "default_agent",
                    f"'{da}' 是 subagent，不能作为 default_agent。"
                    f"OpenCode 会忽略它并 fallback 到 build",
                ))
        elif da not in BUILTIN_PRIMARY:
            issues.append(_warn(
                "default_agent",
                f"'{da}' 不在本方案成员中，也不是内置 primary（build/plan）。"
                f"请确认目标容器上存在该 agent",
            ))

    # ③ subagent_depth 与成员的一致性
    depth = bundle.get("subagent_depth")
    if depth == 0 and subagents:
        issues.append(_warn(
            "subagent_depth",
            f"subagent_depth=0 禁止派生任何 subagent，但方案里有 "
            f"{len(subagents)} 个 subagent，它们永远不会被调用。"
            f"建议改成 1",
        ))

    # ④ 模板 task 规则里指向方案外 agent 的条目
    #
    # 这不是错误 —— 渲染时会按本方案成员**重新合成** permission.task，
    # 方案外的规则不会写进产物（见 agent_render_service.synthesize_task_rule）。
    # 所以只给一条 info 级说明，告诉用户「模板里有这些，但本方案用不上」，
    # 避免用户看到一串 warning 以为配置坏了。
    builtin_subagents = {"general", "explore", "scout"}
    known = agent_names | builtin_subagents
    for a in agents:
        if a.get("mode") not in ("primary", "all"):
            continue
        perm = a.get("permission_json") or {}
        task_rule = perm.get("task")
        if not isinstance(task_rule, dict):
            continue
        outside = [
            pat for pat in task_rule
            if pat != "*" and "*" not in pat and pat not in known
        ]
        if outside:
            issues.append(_info(
                f"members.{a.get('name')}.permission.task",
                f"模板里还有 {len(outside)} 条指向方案外 agent 的规则"
                f"（{', '.join(outside)}）—— 发布时会自动剔除，不写进产物，"
                f"因此不会影响本方案。",
            ))

    # ⑤ 有 primary 能调 subagent 吗？
    if subagents and primaries:
        can_call = False
        for p in primaries:
            perm = p.get("permission_json") or {}
            t = perm.get("task")
            if t is None:
                can_call = True  # 未配置 = 默认允许
                break
            if t == "allow":
                can_call = True
                break
            if isinstance(t, dict):
                # 有任一非 deny 的规则就算能调
                if any(v != "deny" for v in t.values()):
                    can_call = True
                    break
        if not can_call:
            issues.append(_warn(
                "members",
                "所有 primary 的 permission.task 都是 deny，"
                "方案里的 subagent 无法被自动调用（用户仍可 @ 手动召唤）",
            ))

    # ⑥ 全局 permission
    issues.extend(validate_permission(
        bundle.get("global_permission_json"), "global_permission_json",
    ))

    # ⑦ skill 成员重名检测
    skill_names = [s.get("name") for s in skills if s.get("name")]
    dup = {n for n in skill_names if skill_names.count(n) > 1}
    if dup:
        issues.append(_err("members", f"skill 重复：{', '.join(sorted(dup))}"))

    # ⑧ agent 重名检测（会导致落盘文件互相覆盖）
    a_names = [a.get("name") for a in agents if a.get("name")]
    dup_a = {n for n in a_names if a_names.count(n) > 1}
    if dup_a:
        issues.append(_err(
            "members",
            f"agent 重复：{', '.join(sorted(dup_a))}（落盘时文件会互相覆盖）",
        ))

    ok = not any(i.level == "error" for i in issues)
    return ValidationResult(ok=ok, issues=issues)


__all__ = [
    "validate_agent",
    "validate_skill",
    "validate_skill_files",
    "validate_bundle",
    "validate_permission",
    "COMMON_KEY_MISTAKES",
]
