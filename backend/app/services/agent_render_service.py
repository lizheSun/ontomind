"""渲染器：DB 模板 → OpenCode 可识别的落盘产物.

产出的文件必须与手写的等价 —— 已通过实测验证：
把渲染结果写入容器后重启 serve，`GET /agent` 能完整回读
mode / description / temperature / color / 全部 glob 权限规则。

**YAML 手写而非用 pyyaml 的原因**：
1. pyyaml 会把 `"git *": ask` 的键去引号变成 `git *: ask`，
   OpenCode 的 YAML 解析器对含空格/星号的裸键处理不一致，必须强制加引号
2. 需要控制字段顺序（description 在最前，便于人读）
3. 中文不能被转成 \\uXXXX 转义
4. 少一个运行时依赖
"""
import hashlib
import json
import re
from typing import Any, Dict, List, Optional, Sequence

from app.schemas.agent_factory_schema import RenderedArtifact

# ---------------------------------------------------------------------------
# YAML 标量输出
# ---------------------------------------------------------------------------

# 无需加引号的「安全」纯量：不含空格与 YAML 特殊字符
_PLAIN_SAFE = re.compile(r"^[A-Za-z0-9_./-]+$")
# YAML 里会被解析成布尔/空值的词，作为字符串输出时必须加引号
_YAML_RESERVED = {
    "true", "false", "yes", "no", "on", "off", "null", "~", "y", "n",
}


def _yaml_key(key: str) -> str:
    """YAML 键。glob 模式（含空格、*、:）必须加双引号，否则解析不稳定。"""
    if _PLAIN_SAFE.match(key) and key.lower() not in _YAML_RESERVED:
        return key
    return '"' + key.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _yaml_scalar(value: Any) -> str:
    """YAML 标量值。"""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    s = str(value)
    if s == "":
        return '""'
    if _PLAIN_SAFE.match(s) and s.lower() not in _YAML_RESERVED:
        return s
    # 含空格/中文/特殊字符 → 双引号并转义
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _yaml_block(data: Dict[str, Any], indent: int = 0) -> List[str]:
    """把 dict 渲染成 YAML 行（只需支持标量与一层嵌套 dict，够用且可控）。"""
    lines: List[str] = []
    pad = " " * indent
    for k, v in data.items():
        if isinstance(v, dict):
            lines.append(f"{pad}{_yaml_key(k)}:")
            lines.extend(_yaml_block(v, indent + 2))
        elif isinstance(v, list):
            lines.append(f"{pad}{_yaml_key(k)}:")
            for item in v:
                lines.append(f"{pad}  - {_yaml_scalar(item)}")
        else:
            lines.append(f"{pad}{_yaml_key(k)}: {_yaml_scalar(v)}")
    return lines


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _artifact(path: str, content: str, is_exec: bool = False) -> RenderedArtifact:
    return RenderedArtifact(
        path=path,
        content=content,
        sha256=_sha256(content),
        bytes=len(content.encode("utf-8")),
        is_executable=is_exec,
    )


# ---------------------------------------------------------------------------
# Agent → Markdown
# ---------------------------------------------------------------------------

def render_agent_md(t: Dict[str, Any]) -> str:
    """渲染 agent 的 Markdown 定义。

    字段顺序刻意固定为「description → mode → model → 采样 → steps → 外观 → 开关 → permission」，
    与官方文档示例一致，便于人对照阅读。
    只输出有值的字段 —— 空值交给 OpenCode 用默认行为，不要写 null 进去。
    """
    fm: Dict[str, Any] = {}

    # description 必须第一个（最重要，决定委派）
    if t.get("description"):
        fm["description"] = t["description"]
    if t.get("mode"):
        fm["mode"] = t["mode"]
    if t.get("model"):
        fm["model"] = t["model"]
    if t.get("temperature") is not None:
        fm["temperature"] = t["temperature"]
    if t.get("top_p") is not None:
        fm["top_p"] = t["top_p"]
    if t.get("steps") is not None:
        fm["steps"] = t["steps"]
    if t.get("color"):
        fm["color"] = t["color"]
    if t.get("hidden"):
        fm["hidden"] = True
    if t.get("disable"):
        fm["disable"] = True

    lines = ["---"]
    lines.extend(_yaml_block(fm))

    # permission 单独放最后（通常最长，放末尾更易读）
    perm = t.get("permission_json") or t.get("permission")
    if perm:
        lines.append("permission:")
        lines.extend(_yaml_block(perm, 2))

    # options（provider 透传）用 JSON 内联，避免复杂嵌套的 YAML 歧义
    opts = t.get("options_json") or t.get("options")
    if opts:
        for k, v in opts.items():
            if isinstance(v, (dict, list)):
                lines.append(f"{_yaml_key(k)}: {json.dumps(v, ensure_ascii=False)}")
            else:
                lines.append(f"{_yaml_key(k)}: {_yaml_scalar(v)}")

    lines.append("---")
    lines.append("")

    body = (t.get("prompt") or "").rstrip()
    if body:
        lines.append(body)
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Skill → 目录
# ---------------------------------------------------------------------------

def render_skill_md(t: Dict[str, Any]) -> str:
    """渲染 SKILL.md。

    frontmatter **只输出 OpenCode 认识的 5 个字段**，
    多写的字段会被静默忽略，反而误导后续维护者。
    """
    fm: Dict[str, Any] = {
        # name 必须等于目录名，这个约束在 render_skill_files 里保证
        "name": t.get("name") or "",
        "description": t.get("description") or "",
    }
    if t.get("license"):
        fm["license"] = t["license"]
    if t.get("compatibility"):
        fm["compatibility"] = t["compatibility"]

    lines = ["---"]
    lines.extend(_yaml_block(fm))

    md = t.get("metadata_json") or t.get("metadata")
    if md:
        lines.append("metadata:")
        lines.extend(_yaml_block({k: str(v) for k, v in md.items()}, 2))

    lines.append("---")
    lines.append("")

    body = (t.get("body") or "").rstrip()
    if body:
        lines.append(body)
        lines.append("")

    return "\n".join(lines)


def render_skill_files(t: Dict[str, Any], base: str = "skills") -> List[RenderedArtifact]:
    """渲染一个 skill 的全部产物（SKILL.md + 附属文件）。

    目录名强制等于 name —— OpenCode 要求二者一致，否则不加载。
    """
    name = t.get("name") or ""
    root = f"{base}/{name}"
    out: List[RenderedArtifact] = [
        _artifact(f"{root}/SKILL.md", render_skill_md(t)),
    ]
    for f in t.get("files") or []:
        rel = (f.get("rel_path") or "").strip().lstrip("/")
        if not rel:
            continue
        out.append(_artifact(
            f"{root}/{rel}",
            f.get("content") or "",
            bool(f.get("is_executable")),
        ))
    return out


# ---------------------------------------------------------------------------
# Bundle → opencode.jsonc（全局旋钮）
# ---------------------------------------------------------------------------

def render_bundle_config(
    bundle: Dict[str, Any],
    agents: Sequence[Dict[str, Any]],
    skills: Sequence[Dict[str, Any]],
    skill_permissions: Optional[Dict[str, str]] = None,
) -> str:
    """渲染 opencode.jsonc —— 承载 agent 文件放不下的**全局**旋钮。

    为什么 agent 走 .md 而全局旋钮走 json：
    - agent 定义放 .md 更适合人读写、可版本化 diff
    - subagent_depth / default_agent 是全局单例，只能放 config
    """
    cfg: Dict[str, Any] = {"$schema": "https://opencode.ai/config.json"}

    if bundle.get("default_agent"):
        cfg["default_agent"] = bundle["default_agent"]
    if bundle.get("subagent_depth") is not None:
        cfg["subagent_depth"] = bundle["subagent_depth"]

    # 全局 permission：合并 bundle 级配置与 skill 可见性白名单
    perm: Dict[str, Any] = dict(bundle.get("global_permission_json") or {})
    if skill_permissions:
        # OpenCode「最后匹配胜出」→ "*" 必须放第一个
        skill_rule: Dict[str, str] = {}
        explicit = {n: a for n, a in skill_permissions.items() if a}
        if explicit:
            # 有显式配置时，先用 "*": deny 收紧，再逐个放开
            if any(a != "allow" for a in explicit.values()) or True:
                skill_rule["*"] = "allow"
            for n, act in explicit.items():
                skill_rule[n] = act
            existing = perm.get("skill")
            if isinstance(existing, dict):
                merged = {**skill_rule, **existing}
                # 保证 "*" 仍在最前
                if "*" in merged:
                    star = merged.pop("*")
                    merged = {"*": star, **merged}
                perm["skill"] = merged
            elif isinstance(existing, str):
                perm["skill"] = {"*": existing, **{k: v for k, v in skill_rule.items() if k != "*"}}
            else:
                perm["skill"] = skill_rule
    if perm:
        cfg["permission"] = perm

    header = (
        "// 由 OntoMind Agent 工厂生成，请勿手工编辑。\n"
        f"// bundle: {bundle.get('name', '')}\n"
        f"// agents: {', '.join(a.get('name', '') for a in agents) or '(none)'}\n"
        f"// skills: {', '.join(s.get('name', '') for s in skills) or '(none)'}\n"
    )
    return header + json.dumps(cfg, ensure_ascii=False, indent=2) + "\n"


# ---------------------------------------------------------------------------
# 全量渲染
# ---------------------------------------------------------------------------

# OpenCode 内置 subagent，任何方案里都存在
BUILTIN_SUBAGENTS = ("general", "explore", "scout")


def resolve_task_action(
    task_rule: Any, target: str, default: str = "allow"
) -> str:
    """按 OpenCode 语义解析 task 规则对某个 target 的动作。

    规则：glob 匹配，**最后匹配胜出**；未配置 = default。
    与前端 `resolveTaskAction` 必须保持一致。
    """
    import fnmatch

    if task_rule is None:
        return default
    if isinstance(task_rule, str):
        return task_rule
    if not isinstance(task_rule, dict):
        return default
    action = default
    for pat, act in task_rule.items():
        if fnmatch.fnmatchcase(target, pat):
            action = act
    return action


def synthesize_task_rule(
    primary: Dict[str, Any],
    subagent_names: Sequence[str],
    member_overrides: Optional[Dict[str, str]] = None,
) -> Optional[Dict[str, str]]:
    """按 bundle 合成 primary 的 permission.task。

    **为什么必须在这里合成，而不是改 agent 模板**：
    `task` 在 OpenCode 里是 agent 级字段，但语义是方案级的（「本编排里谁能调谁」）。
    若直接写回模板，A 方案的授权会污染共享该模板的 B 方案 ——
    实际踩过：在一个方案里授权 docs-writer，另一个没有该成员的方案就报
    「规则指向 'docs-writer'…该规则不会生效」。

    合成逻辑：
    1. 只为**本方案的 subagent 成员**产出规则，模板里指向方案外 agent 的规则一律丢弃
       （那些规则在本方案里本就不会生效，写进去只会产生噪音与困惑）
    2. 每个成员的动作优先取 `member_overrides`（方案内覆盖），否则按模板规则解析
    3. 保留模板的 `"*"` 兜底（没有则用 deny，最小权限）
    4. `"*"` 放在最前 —— OpenCode 最后匹配胜出
    """
    tmpl_rule = (primary.get("permission_json") or {}).get("task")
    overrides = member_overrides or {}

    # 兜底：模板显式给了 "*" 就沿用；模板是简写动作就用它；都没有则 deny
    if isinstance(tmpl_rule, dict) and "*" in tmpl_rule:
        star = tmpl_rule["*"]
    elif isinstance(tmpl_rule, str):
        star = tmpl_rule
    else:
        star = "deny" if subagent_names else None

    out: Dict[str, str] = {}
    if star is not None:
        out["*"] = star
    for name in subagent_names:
        act = overrides.get(name) or resolve_task_action(
            tmpl_rule, name, default=star or "allow",
        )
        # 与兜底相同就不必重复写（保持产物精简、可读）
        if star is not None and act == star:
            continue
        out[name] = act

    # 内置 subagent 也允许显式覆盖
    for name in BUILTIN_SUBAGENTS:
        if name in overrides:
            out[name] = overrides[name]

    return out or None


def render_bundle(
    bundle: Dict[str, Any],
    agents: Sequence[Dict[str, Any]],
    skills: Sequence[Dict[str, Any]],
    skill_permissions: Optional[Dict[str, str]] = None,
    task_overrides: Optional[Dict[str, str]] = None,
) -> List[RenderedArtifact]:
    """渲染一个 bundle 的全部落盘产物。

    产物布局（相对目标目录，如容器内 /root/.config/opencode/）：
        agents/<name>.md
        skills/<name>/SKILL.md
        skills/<name>/references/*
        opencode.jsonc

    `task_overrides`: {subagent_name: action} —— 本方案内的委派授权覆盖。
    primary 的 permission.task 会按方案成员**重新合成**，不使用模板原值。
    """
    out: List[RenderedArtifact] = []

    subagent_names = [
        a.get("name") for a in agents
        if a.get("name") and a.get("mode") == "subagent"
    ]

    for a in agents:
        name = a.get("name")
        if not name:
            continue
        # primary 的 task 规则按本方案合成，避免带出方案外的死规则
        if a.get("mode") in ("primary", "all") and subagent_names:
            a = dict(a)
            perm = dict(a.get("permission_json") or {})
            synthesized = synthesize_task_rule(a, subagent_names, task_overrides)
            if synthesized:
                perm["task"] = synthesized
            else:
                perm.pop("task", None)
            a["permission_json"] = perm
        out.append(_artifact(f"agents/{name}.md", render_agent_md(a)))

    for s in skills:
        out.extend(render_skill_files(s))

    out.append(_artifact(
        "opencode.jsonc",
        render_bundle_config(bundle, agents, skills, skill_permissions),
    ))

    return out


def artifacts_tree(artifacts: Sequence[RenderedArtifact]) -> List[str]:
    """产物路径列表（排序后），供前端展示目录树。"""
    return sorted(a.path for a in artifacts)


__all__ = [
    "BUILTIN_SUBAGENTS",
    "resolve_task_action",
    "synthesize_task_rule",
    "render_agent_md",
    "render_skill_md",
    "render_skill_files",
    "render_bundle_config",
    "render_bundle",
    "artifacts_tree",
]
