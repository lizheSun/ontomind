"""Skill 双平面渲染器 —— 导出合规 OpenCode 目录 + 治理清单.

**核心职责：保证产出物 100% 合规**（约束 1）

实测依据（OpenCode v1.18.12 真机，见 docs/PRD-skill-platform.md §1）：
- frontmatter 顶层塞治理字段 → skill 能加载，但字段被**静默忽略**（配置永不生效）
- 同样信息放 `metadata:` → 保留在文件里，可供追溯

所以：
- **执行平面**：SKILL.md 只输出 5 个合法字段（name/description/license/compatibility/metadata）
- **治理摘要**：以 `metadata.omd_*` 导出（`omd_` 前缀避免与未来官方字段冲突）
- **治理全量**：导出到 `_ontomind/skill.manifest.json`，刻意放在 OpenCode 扫描路径**之外**
  （若放进 skills/ 会被当成一个 skill 目录扫描）

目录规范（约束 2）：
- 项目级 `.opencode/skills/<skill-name>/`
- 全局级 `~/.config/opencode/skills/<skill-name>/`
"""
import hashlib
import json
import re
from typing import Any, Dict, List, Optional, Sequence

from app.schemas.skill_platform_schema import ExportedFile

# ---------------------------------------------------------------------------
# 目录规范（约束 2）
# ---------------------------------------------------------------------------

SCOPE_PREFIX = {
    "project": ".opencode/skills",
    "global": "~/.config/opencode/skills",
}

# 治理平面产物目录 —— 必须在 skills/ 之外
CONTROL_DIR = "_ontomind"

# 治理摘要在 metadata 里的前缀
OMD_PREFIX = "omd_"


# ---------------------------------------------------------------------------
# YAML 输出（与 agent_render_service 同一套策略，保证 glob 键加引号、中文不转义）
# ---------------------------------------------------------------------------

_PLAIN_SAFE = re.compile(r"^[A-Za-z0-9_./-]+$")
_YAML_RESERVED = {"true", "false", "yes", "no", "on", "off", "null", "~", "y", "n"}


def _yaml_key(key: str) -> str:
    if _PLAIN_SAFE.match(key) and key.lower() not in _YAML_RESERVED:
        return key
    return '"' + key.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _yaml_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    s = str(value)
    if s == "":
        return '""'
    if _PLAIN_SAFE.match(s) and s.lower() not in _YAML_RESERVED:
        return s
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _file(
    path: str, content: str, is_exec: bool = False, plane: str = "data"
) -> ExportedFile:
    return ExportedFile(
        path=path,
        content=content,
        sha256=_sha256(content),
        bytes=len(content.encode("utf-8")),
        is_executable=is_exec,
        plane=plane,  # type: ignore[arg-type]
    )


# ---------------------------------------------------------------------------
# 治理摘要 → metadata.omd_*
# ---------------------------------------------------------------------------

def build_governance_metadata(
    meta: Dict[str, Any],
    policy: Optional[Dict[str, Any]] = None,
    version: Optional[int] = None,
    include_manifest_ref: bool = True,
) -> Dict[str, str]:
    """把治理摘要转成 metadata（**值必须是 string** —— OpenCode 硬要求）。

    只放「排障时最有用」的少量字段，不做全量搬运 ——
    metadata 会常驻上下文，塞太多会挤占模型的注意力预算。
    """
    out: Dict[str, str] = {}

    def put(key: str, value: Any) -> None:
        if value is None or value == "" or value == []:
            return
        if isinstance(value, bool):
            out[OMD_PREFIX + key] = "true" if value else "false"
        else:
            out[OMD_PREFIX + key] = str(value)

    put("skill_kind", meta.get("skill_kind"))
    put("risk_level", meta.get("risk_level"))
    put("lifecycle", meta.get("lifecycle"))
    put("owner", meta.get("owner"))
    put("biz_line", meta.get("biz_line"))
    if version is not None:
        put("version", version)
    put("qps_limit", meta.get("qps_limit"))
    put("session_call_limit", meta.get("session_call_limit"))
    if policy:
        put("require_confirm", policy.get("require_confirm"))
        if policy.get("circuit_threshold"):
            put("circuit_threshold", policy.get("circuit_threshold"))
    if include_manifest_ref:
        out[OMD_PREFIX + "manifest"] = f"{CONTROL_DIR}/skill.manifest.json"

    return out


# ---------------------------------------------------------------------------
# SKILL.md（执行平面，100% 合规）
# ---------------------------------------------------------------------------

def render_skill_md(
    name: str,
    description: str,
    body: Optional[str] = None,
    license_: Optional[str] = None,
    compatibility: Optional[str] = None,
    user_metadata: Optional[Dict[str, str]] = None,
    governance_metadata: Optional[Dict[str, str]] = None,
) -> str:
    """渲染 SKILL.md。

    **只输出 5 个合法 frontmatter 字段** —— 治理字段绝不出现在顶层，
    否则产出物不合规、且那些配置会被 OpenCode 静默忽略。
    """
    lines = ["---"]
    # name 与目录名强制一致（约束 3），由调用方保证目录用同一个 name
    lines.append(f"{_yaml_key('name')}: {_yaml_scalar(name)}")
    lines.append(f"{_yaml_key('description')}: {_yaml_scalar(description)}")
    if license_:
        lines.append(f"{_yaml_key('license')}: {_yaml_scalar(license_)}")
    if compatibility:
        lines.append(f"{_yaml_key('compatibility')}: {_yaml_scalar(compatibility)}")

    # metadata：用户自定义 + 治理摘要（omd_ 前缀），全部转 string
    merged: Dict[str, str] = {}
    for k, v in (user_metadata or {}).items():
        merged[str(k)] = str(v)
    for k, v in (governance_metadata or {}).items():
        merged[str(k)] = str(v)
    if merged:
        lines.append("metadata:")
        for k in sorted(merged.keys()):
            lines.append(f"  {_yaml_key(k)}: {_yaml_scalar(merged[k])}")

    lines.append("---")
    lines.append("")

    text = (body or "").rstrip()
    if text:
        lines.append(text)
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 治理清单（治理平面）
# ---------------------------------------------------------------------------

def render_manifest(data: Dict[str, Any]) -> str:
    """渲染 _ontomind/skill.manifest.json —— 治理平面全量配置。

    ⚠️ 这里**绝不包含明文密钥**，只有配置中心引用键（约束 5）。
    平台 Skill 网关读这份清单来执行鉴权/限流/校验/熔断/脱敏。
    """
    meta = data.get("meta") or {}
    exec_api = dict(data.get("exec_api") or {})

    # 双重保险：即使上游漏了，导出时也把可疑字段剥掉
    exec_api.pop("secret", None)
    exec_api.pop("secret_value", None)
    exec_api.pop("ak", None)
    exec_api.pop("sk", None)

    manifest: Dict[str, Any] = {
        "$schema": "https://ontomind.internal/schema/skill-manifest-v1.json",
        "generated_by": "OntoMind Skill Platform",
        "note": (
            "治理平面配置。OpenCode 不读取本文件 —— "
            "限流/熔断/RBAC/脱敏由 OntoMind Skill 网关执行。"
            "本文件不含明文密钥，仅含配置中心引用键。"
        ),
        "skill": {
            "name": data.get("name"),
            "description": data.get("description"),
            "display_name": data.get("display_name"),
            "category": data.get("category"),
            "version": data.get("current_version", 1),
        },
        "meta": {
            "skill_kind": meta.get("skill_kind"),
            "name_zh": meta.get("name_zh"),
            "name_en": meta.get("name_en"),
            "biz_tags": meta.get("biz_tags") or [],
            "risk_level": meta.get("risk_level"),
            "owner": meta.get("owner"),
            "owner_email": meta.get("owner_email"),
            "biz_line": meta.get("biz_line"),
            "qps_limit": meta.get("qps_limit"),
            "session_call_limit": meta.get("session_call_limit"),
            "lifecycle": meta.get("lifecycle"),
        },
        "contract": {
            # 标准出参外壳（需求指定）
            "output_envelope": ["code", "msg", "data", "session_vars"],
            "input_schema": build_json_schema(data.get("params_in") or []),
            "output_data_schema": build_json_schema(data.get("params_out") or []),
            "params_in": _clean_params(data.get("params_in") or []),
            "params_out": _clean_params(data.get("params_out") or []),
        },
        "execution": {
            "kind": meta.get("skill_kind"),
            "prompt": data.get("exec_prompt"),
            "api": exec_api or None,
            "flow": data.get("exec_flow"),
        },
        "policy": data.get("policy"),
    }
    return json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"


def _clean_params(params: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """导出参数定义时剔除 DB 内部字段。"""
    drop = {"id", "direction", "created_at", "updated_at", "skill_template_id"}
    return [{k: v for k, v in p.items() if k not in drop} for p in params]


# ---------------------------------------------------------------------------
# JSON Schema 生成（模块 2 的核心产出）
# ---------------------------------------------------------------------------

def build_json_schema(params: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """把可视化配置的参数列表编译成标准 JSON Schema（Draft 2020-12）。

    网关用它做入参校验；前端也用它做在线调试。
    """
    props: Dict[str, Any] = {}
    required: List[str] = []

    for p in params:
        name = p.get("name")
        if not name:
            continue
        dtype = p.get("data_type") or "string"
        node: Dict[str, Any] = {"type": dtype}

        if p.get("title"):
            node["title"] = p["title"]
        if p.get("description"):
            node["description"] = p["description"]

        enums = p.get("enum_values") or []
        if enums:
            if dtype in ("number", "integer"):
                try:
                    node["enum"] = [
                        int(e) if dtype == "integer" else float(e) for e in enums
                    ]
                except (TypeError, ValueError):
                    node["enum"] = list(enums)
            elif dtype == "boolean":
                node["enum"] = [str(e).lower() == "true" for e in enums]
            else:
                node["enum"] = list(enums)

        if dtype == "string":
            if p.get("regex_pattern"):
                node["pattern"] = p["regex_pattern"]
            if p.get("min_val") is not None:
                node["minLength"] = int(p["min_val"])
            if p.get("max_val") is not None:
                node["maxLength"] = int(p["max_val"])
        elif dtype in ("number", "integer"):
            if p.get("min_val") is not None:
                node["minimum"] = p["min_val"]
            if p.get("max_val") is not None:
                node["maximum"] = p["max_val"]
        elif dtype == "array":
            node["items"] = {}
            if p.get("min_val") is not None:
                node["minItems"] = int(p["min_val"])
            if p.get("max_val") is not None:
                node["maxItems"] = int(p["max_val"])

        dv = p.get("default_value")
        if dv not in (None, ""):
            node["default"] = _coerce(dv, dtype)

        # 平台扩展字段（x- 前缀，符合 JSON Schema 惯例，不影响标准校验器）
        if p.get("source"):
            node["x-source"] = p["source"]
        if p.get("context_key"):
            node["x-context-key"] = p["context_key"]
        if p.get("mask_rule") and p["mask_rule"] != "none":
            node["x-mask"] = p["mask_rule"]
        if p.get("filtered"):
            node["x-filtered"] = True
        if p.get("write_to_context"):
            node["x-write-context"] = p.get("context_write_key") or name

        props[name] = node
        if p.get("required"):
            required.append(name)

    schema: Dict[str, Any] = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": props,
        "additionalProperties": False,
    }
    if required:
        schema["required"] = required
    return schema


def _coerce(value: Any, dtype: str) -> Any:
    """按声明类型转换默认值。"""
    try:
        if dtype == "integer":
            return int(value)
        if dtype == "number":
            return float(value)
        if dtype == "boolean":
            return str(value).lower() == "true"
        if dtype in ("object", "array"):
            return json.loads(value) if isinstance(value, str) else value
    except (TypeError, ValueError, json.JSONDecodeError):
        return value
    return value


# ---------------------------------------------------------------------------
# 全量导出（约束 1、2、非功能 3）
# ---------------------------------------------------------------------------

def export_skill(
    data: Dict[str, Any],
    scope: str = "project",
    include_manifest: bool = True,
) -> List[ExportedFile]:
    """导出一个 Skill 的完整目录包。

    产出结构（scope=project）：
        .opencode/skills/<name>/SKILL.md          ← 执行平面，100% 合规
        .opencode/skills/<name>/references/*.md
        .opencode/skills/<name>/scripts/*
        _ontomind/skill.manifest.json             ← 治理平面（在 skills/ 之外）
        _ontomind/README.md
    """
    name = (data.get("name") or "").strip()
    if not name:
        raise ValueError("Skill 名不能为空")

    prefix = SCOPE_PREFIX.get(scope, SCOPE_PREFIX["project"])
    # 目录名强制 == name（约束 3）
    root = f"{prefix}/{name}"

    meta = data.get("meta") or {}
    policy = data.get("policy")

    gov_meta = build_governance_metadata(
        meta, policy, data.get("current_version"), include_manifest and True,
    )

    out: List[ExportedFile] = [
        _file(
            f"{root}/SKILL.md",
            render_skill_md(
                name=name,
                description=data.get("description") or "",
                body=data.get("body"),
                license_=data.get("license"),
                compatibility=data.get("compatibility"),
                user_metadata=data.get("metadata_json"),
                governance_metadata=gov_meta,
            ),
            plane="data",
        )
    ]

    # 附属文件（渐进披露）
    for f in data.get("files") or []:
        rel = (f.get("rel_path") or "").strip().lstrip("/")
        if not rel:
            continue
        out.append(_file(
            f"{root}/{rel}",
            f.get("content") or "",
            bool(f.get("is_executable")),
            plane="data",
        ))

    if include_manifest:
        out.append(_file(
            f"{CONTROL_DIR}/skill.manifest.json",
            render_manifest(data),
            plane="control",
        ))
        out.append(_file(
            f"{CONTROL_DIR}/README.md",
            render_deploy_readme(name, scope),
            plane="control",
        ))

    return out


def render_deploy_readme(name: str, scope: str) -> str:
    """部署落地说明（非功能要求 4）。"""
    target = (
        "项目根目录（与 .opencode 同级）"
        if scope == "project"
        else "用户主目录（~）"
    )
    path = SCOPE_PREFIX.get(scope, SCOPE_PREFIX["project"])
    return f"""# 部署说明 — {name}

本包由 **OntoMind Skill 平台**导出，采用双平面结构。

## 目录说明

| 路径 | 平面 | 说明 |
|---|---|---|
| `{path}/{name}/` | 执行平面 | OpenCode 原生 Skill，**直接加载生效** |
| `_ontomind/skill.manifest.json` | 治理平面 | 限流/熔断/RBAC/脱敏配置，由 OntoMind Skill 网关读取 |

> ⚠️ `_ontomind/` **刻意放在 skills/ 之外** —— 若放进去会被 OpenCode 当成一个 skill 目录扫描。

## 部署步骤

1. 把 `{path}/` 解压到{target}
2. 重启 opencode 服务使其重新扫描 skill 目录：
   ```bash
   opencode serve --port 4096 --hostname 0.0.0.0 --cors http://localhost:5173
   ```
   > 实测：写文件后**不重启不会热感知**，必须重启。
3. 验证已被加载：
   ```bash
   opencode run --agent build "列出你可用的 skills 名称清单，只输出名称"
   ```
   输出里应包含 `{name}`。

## 治理配置如何生效

`skill.manifest.json` 里的限流、熔断、RBAC、脱敏等配置 **OpenCode 不识别**，
需由 OntoMind Skill 网关在调用链上执行：

```
鉴权(RBAC) → 限流(QPS/会话频次) → 入参校验(JSON Schema) → 执行
  → 熔断降级 → 出参脱敏/过滤 → 会话变量写入 → Trace 落库
```

未接入网关时，`SKILL.md` 仍可正常工作，但治理策略**不会生效**。

## 注意

- 本包**不含明文密钥**。`execution.api.secret_ref` 是配置中心引用键，
  需在目标环境的配置中心中预先托管对应密钥。
- 目录名与 `SKILL.md` 的 `name` 字段必须一致，请勿重命名目录。
"""


def export_tree(files: Sequence[ExportedFile]) -> List[str]:
    return sorted(f.path for f in files)


__all__ = [
    "SCOPE_PREFIX",
    "CONTROL_DIR",
    "OMD_PREFIX",
    "build_governance_metadata",
    "render_skill_md",
    "render_manifest",
    "build_json_schema",
    "export_skill",
    "render_deploy_readme",
    "export_tree",
]
