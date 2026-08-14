"""Skill 平台校验器 —— 17 条规则，实时拦截违规配置.

**为什么校验必须前置**（非功能要求 2）：
1. OpenCode 对非法 frontmatter 字段**静默忽略** —— 写错不报错也不生效
2. 明文密钥一旦入库就是安全事故，事后清理无法挽回（约束 5）
3. 生命周期非法迁移会让「测试中」的技能直接上生产

规则分三级：
- `error`   阻断保存/发布
- `warning` 提示「这样可能不是你想要的」
- `info`    纯说明（配置合法，讲清会发生什么）
"""
import re
from typing import Any, Dict, List, Optional, Sequence

from app.db.models.skill_platform_model import (
    LIFECYCLE_GATED,
    LIFECYCLE_TRANSITIONS,
)
from app.schemas.skill_platform_schema import (
    SKILL_NAME_PATTERN,
    SkillIssue,
    SkillValidation,
)

# ---------------------------------------------------------------------------
# 明文密钥识别（约束 5 的核心）
#
# 这些模式覆盖主流云厂商与平台的密钥格式。宁可误报（用户可换成引用键）
# 也不能漏报 —— 明文密钥入库是不可逆的安全事故。
# ---------------------------------------------------------------------------

_SECRET_PATTERNS: List[tuple] = [
    (re.compile(r"^AKIA[0-9A-Z]{12,}$"), "AWS Access Key"),
    (re.compile(r"^ASIA[0-9A-Z]{12,}$"), "AWS 临时 Key"),
    (re.compile(r"^AKLT[0-9A-Za-z_-]{10,}$"), "火山引擎 AK"),
    (re.compile(r"^LTAI[0-9A-Za-z]{12,}$"), "阿里云 AK"),
    (re.compile(r"^sk-[0-9A-Za-z_-]{16,}$"), "OpenAI 风格 Key"),
    (re.compile(r"^ark-[0-9a-f-]{20,}$"), "方舟 API Key"),
    (re.compile(r"^gh[pousr]_[0-9A-Za-z]{16,}$"), "GitHub Token"),
    (re.compile(r"^xox[baprs]-[0-9A-Za-z-]{10,}$"), "Slack Token"),
    (re.compile(r"^eyJ[0-9A-Za-z_-]{20,}\.[0-9A-Za-z_-]{10,}"), "JWT"),
    (re.compile(r"^-----BEGIN [A-Z ]*PRIVATE KEY-----"), "私钥 PEM"),
]

# 兜底：长随机串（高熵）也视为可疑
_LONG_HEX = re.compile(r"^[0-9a-fA-F]{32,}$")
_LONG_B64 = re.compile(r"^[A-Za-z0-9+/]{40,}={0,2}$")

# 合法的配置中心引用键格式
_SECRET_REF_OK = re.compile(r"^(cc|kms|vault|sm|env)://[\w\-./]+$")

_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def detect_plaintext_secret(value: str) -> Optional[str]:
    """判断字符串是否像明文密钥。返回命中的类型名，未命中返回 None。"""
    v = (value or "").strip()
    if not v or len(v) < 12:
        return None
    # 已是合法引用键 → 放行
    if _SECRET_REF_OK.match(v):
        return None
    for pat, label in _SECRET_PATTERNS:
        if pat.match(v):
            return label
    if _LONG_HEX.match(v):
        return "长十六进制串（疑似密钥/哈希）"
    if _LONG_B64.match(v) and not v.startswith(("http://", "https://")):
        return "长 Base64 串（疑似密钥）"
    return None


def _err(field: str, message: str, module: Optional[str] = None) -> SkillIssue:
    return SkillIssue(level="error", field=field, message=message, module=module)


def _warn(field: str, message: str, module: Optional[str] = None) -> SkillIssue:
    return SkillIssue(level="warning", field=field, message=message, module=module)


def _info(field: str, message: str, module: Optional[str] = None) -> SkillIssue:
    return SkillIssue(level="info", field=field, message=message, module=module)


# ---------------------------------------------------------------------------
# 规则 1–5、17：OpenCode 合规（约束 1、2、3）
# ---------------------------------------------------------------------------

def validate_opencode_compliance(
    name: str,
    description: str,
    metadata: Optional[Dict[str, Any]],
    files: Sequence[Dict[str, Any]],
    body: Optional[str],
) -> List[SkillIssue]:
    """OpenCode 原生规范校验 —— 不过这关的配置导出后不会被加载。"""
    issues: List[SkillIssue] = []
    M = "compliance"

    # ① kebab-case（约束 3）
    n = (name or "").strip()
    if not n:
        issues.append(_err("name", "Skill 唯一标识不能为空", M))
    elif not re.match(SKILL_NAME_PATTERN, n):
        issues.append(_err(
            "name",
            f"'{n}' 不符合 kebab-case 规范。只能用小写字母、数字和单个连字符分隔，"
            f"不能以 '-' 开头/结尾，不能有连续 '--'。例：pay-order-query",
            M,
        ))
    elif len(n) > 64:
        issues.append(_err("name", f"标识 {len(n)} 字符，超过 64 上限", M))
    else:
        # ② 目录名一致性（约束 3）—— 渲染器强制用 name 作目录名，这里只做说明
        issues.append(_info(
            "name",
            f"落盘目录名将强制使用 '{n}'，与 SKILL.md 的 name 字段保持一致",
            M,
        ))

    # ③ description
    d = (description or "").strip()
    if not d:
        issues.append(_err(
            "description",
            "描述不能为空 —— 这是模型判断「何时加载该 Skill」的唯一依据",
            M,
        ))
    elif len(d) > 1024:
        issues.append(_err(
            "description", f"描述 {len(d)} 字符，超过 OpenCode 的 1024 上限", M,
        ))
    elif len(d) < 20:
        issues.append(_warn(
            "description",
            "描述过短。建议写清「我做什么 + 什么场景触发我」，否则模型可能不会加载它",
            M,
        ))

    # ④ metadata 必须 string→string
    if metadata is not None:
        if not isinstance(metadata, dict):
            issues.append(_err("metadata", "metadata 必须是对象", M))
        else:
            for k, v in metadata.items():
                if not isinstance(v, str):
                    issues.append(_err(
                        f"metadata.{k}",
                        f"metadata 的值必须是字符串（当前 {type(v).__name__}）—— "
                        f"OpenCode 只接受 string→string 映射",
                        M,
                    ))

    # ⑤ 附属文件路径安全
    seen = set()
    for idx, f in enumerate(files or []):
        rel = (f.get("rel_path") or "").strip()
        path = f"files[{idx}].rel_path"
        if not rel:
            issues.append(_err(path, "路径不能为空", M))
            continue
        if rel.startswith("/") or (len(rel) > 1 and rel[1] == ":"):
            issues.append(_err(path, f"'{rel}' 不能是绝对路径", M))
            continue
        if ".." in rel.split("/"):
            issues.append(_err(path, f"'{rel}' 含 '..'，禁止路径穿越", M))
            continue
        if rel.upper() == "SKILL.MD":
            issues.append(_err(
                path, "SKILL.md 由正文字段生成，不要作为附属文件重复添加", M,
            ))
            continue
        if rel in seen:
            issues.append(_err(path, f"路径 '{rel}' 重复", M))
            continue
        seen.add(rel)
        if len((f.get("content") or "").encode("utf-8")) > 1024 * 1024:
            issues.append(_err(f"files[{idx}].content", f"'{rel}' 超过单文件 1MB 上限", M))

    # ⑰ 渐进披露建议
    body_lines = (body or "").count("\n") + 1 if body else 0
    if body_lines > 400 and not files:
        issues.append(_warn(
            "body",
            f"正文约 {body_lines} 行且没有附属文件。SKILL.md 会常驻上下文，"
            f"建议把低频细节下沉到 references/*.md（渐进披露）",
            M,
        ))

    return issues


# ---------------------------------------------------------------------------
# 规则 6–7：密钥安全（约束 5）
# ---------------------------------------------------------------------------

def validate_secrets(exec_api: Optional[Dict[str, Any]]) -> List[SkillIssue]:
    """密钥必须走配置中心，禁止明文入库。"""
    issues: List[SkillIssue] = []
    M = "security"
    if not exec_api:
        return issues

    auth_type = exec_api.get("auth_type") or "none"
    ref = (exec_api.get("secret_ref") or "").strip()

    # ⑥ 明文密钥拦截
    if ref:
        hit = detect_plaintext_secret(ref)
        if hit:
            issues.append(_err(
                "exec_api.secret_ref",
                f"检测到疑似明文密钥（{hit}）。按安全约束，密钥禁止明文存储，"
                f"请改填配置中心引用键，如 cc://skill/<skill-name>/aksk",
                M,
            ))
        elif not _SECRET_REF_OK.match(ref):
            issues.append(_warn(
                "exec_api.secret_ref",
                f"'{ref}' 不像配置中心引用键。推荐格式 "
                f"cc:// | kms:// | vault:// | sm:// | env:// 开头，例：cc://skill/pay/aksk",
                M,
            ))

    # ⑦ 需要鉴权但没配引用键
    if auth_type != "none" and not ref:
        issues.append(_err(
            "exec_api.secret_ref",
            f"鉴权方式为 {auth_type} 但未配置密钥引用键。"
            f"请在配置中心托管密钥后填入引用键（禁止明文）",
            M,
        ))

    # 请求头里也不能藏密钥
    for k, v in (exec_api.get("headers") or {}).items():
        hit = detect_plaintext_secret(str(v))
        if hit:
            issues.append(_err(
                f"exec_api.headers.{k}",
                f"请求头 '{k}' 的值疑似明文密钥（{hit}）。"
                f"请改用鉴权方式 + 配置中心引用键，不要写死在请求头里",
                M,
            ))
        elif k.lower() in ("authorization", "x-api-key", "x-auth-token") and v:
            issues.append(_warn(
                f"exec_api.headers.{k}",
                f"'{k}' 是鉴权头，建议改用「鉴权方式 + 密钥引用键」配置，"
                f"由网关在调用时注入，避免配置泄露",
                M,
            ))

    return issues


# ---------------------------------------------------------------------------
# 规则 8–10、16：治理与上线门禁（模块 1、5）
# ---------------------------------------------------------------------------

def validate_meta(
    meta: Dict[str, Any],
    policy: Optional[Dict[str, Any]] = None,
    params_out: Optional[Sequence[Dict[str, Any]]] = None,
    exec_api: Optional[Dict[str, Any]] = None,
) -> List[SkillIssue]:
    issues: List[SkillIssue] = []
    M = "meta"

    lifecycle = meta.get("lifecycle") or "draft"
    risk = meta.get("risk_level") or "low"
    kind = meta.get("skill_kind") or "prompt"

    # ⑧ 高危技能应开二次确认
    if risk == "high":
        if not (policy or {}).get("require_confirm"):
            issues.append(_warn(
                "policy.require_confirm",
                "风险等级为「高危资金操作」但未开启二次确认。"
                "建议开启，避免模型误调用造成资金损失",
                "security",
            ))
        if not meta.get("owner"):
            issues.append(_err(
                "meta.owner", "高危技能必须指定责任人", M,
            ))

    # ⑩ 上线门禁：进入 canary/released 前必须配齐
    if lifecycle in LIFECYCLE_GATED:
        if not meta.get("owner"):
            issues.append(_err(
                "meta.owner", f"进入「{lifecycle}」前必须指定责任人", M,
            ))
        if not meta.get("biz_line"):
            issues.append(_warn(
                "meta.biz_line", f"进入「{lifecycle}」建议填写归属业务线，便于运维归属", M,
            ))
        if not params_out:
            issues.append(_err(
                "params_out",
                f"进入「{lifecycle}」前必须定义出参结构（data 内部字段），"
                f"否则调用方无法解析返回值",
                "params",
            ))
        # ⑯ API 型上线必须有生产地址
        if kind == "api" and lifecycle == "released":
            if not (exec_api or {}).get("url_prod"):
                issues.append(_err(
                    "exec_api.url_prod",
                    "API 型技能正式上线前必须配置生产环境地址，"
                    "否则会打到测试环境",
                    "exec",
                ))

    if meta.get("qps_limit") is None and lifecycle in LIFECYCLE_GATED:
        issues.append(_warn(
            "meta.qps_limit",
            f"进入「{lifecycle}」未设限流 QPS，异常流量可能打穿下游",
            M,
        ))

    return issues


def validate_lifecycle_transition(
    current: str, target: str
) -> List[SkillIssue]:
    """⑨ 生命周期迁移合法性。"""
    if current == target:
        return []
    allowed = LIFECYCLE_TRANSITIONS.get(current, [])
    if target not in allowed:
        readable = "、".join(allowed) if allowed else "（终态，不可再流转）"
        return [_err(
            "meta.lifecycle",
            f"不允许从「{current}」直接流转到「{target}」。"
            f"当前状态可流转到：{readable}",
            "meta",
        )]
    return []


# ---------------------------------------------------------------------------
# 规则 11–13：参数契约（模块 2）
# ---------------------------------------------------------------------------

def validate_params(
    params: Sequence[Dict[str, Any]], direction: str
) -> List[SkillIssue]:
    issues: List[SkillIssue] = []
    M = "params"
    prefix = "params_in" if direction == "in" else "params_out"
    seen = set()

    for idx, p in enumerate(params or []):
        name = (p.get("name") or "").strip()
        path = f"{prefix}[{idx}]"

        # ⑪ 参数名
        if not name:
            issues.append(_err(f"{path}.name", "参数名不能为空", M))
            continue
        if not _IDENT.match(name):
            issues.append(_err(
                f"{path}.name",
                f"'{name}' 不是合法参数名。只能字母/数字/下划线，且不能数字开头",
                M,
            ))
        if name in seen:
            issues.append(_err(f"{path}.name", f"参数名 '{name}' 重复", M))
            continue
        seen.add(name)

        dtype = p.get("data_type") or "string"

        # ⑫ 枚举与类型匹配
        enums = p.get("enum_values") or []
        if enums:
            if dtype in ("object", "array"):
                issues.append(_err(
                    f"{path}.enum_values",
                    f"{dtype} 类型不支持枚举约束",
                    M,
                ))
            elif dtype in ("number", "integer"):
                for e in enums:
                    try:
                        float(e)
                    except (TypeError, ValueError):
                        issues.append(_err(
                            f"{path}.enum_values",
                            f"枚举值 '{e}' 不是合法数字（参数类型为 {dtype}）",
                            M,
                        ))
            elif dtype == "boolean":
                for e in enums:
                    if str(e).lower() not in ("true", "false"):
                        issues.append(_err(
                            f"{path}.enum_values",
                            f"枚举值 '{e}' 不是布尔值",
                            M,
                        ))

        # ⑬ 正则合法性
        rx = p.get("regex_pattern")
        if rx:
            if dtype != "string":
                issues.append(_warn(
                    f"{path}.regex_pattern",
                    f"正则校验只对 string 生效，当前类型是 {dtype}",
                    M,
                ))
            try:
                re.compile(rx)
            except re.error as e:
                issues.append(_err(
                    f"{path}.regex_pattern", f"正则表达式非法：{e}", M,
                ))

        # 默认值与类型
        dv = p.get("default_value")
        if dv not in (None, ""):
            if dtype in ("number", "integer"):
                try:
                    float(dv)
                except (TypeError, ValueError):
                    issues.append(_err(
                        f"{path}.default_value", f"默认值 '{dv}' 不是合法数字", M,
                    ))
            elif dtype == "boolean" and str(dv).lower() not in ("true", "false"):
                issues.append(_err(
                    f"{path}.default_value", f"默认值 '{dv}' 不是布尔值", M,
                ))

        # 来源一致性
        if direction == "in":
            src = p.get("source") or "dialog"
            if src == "context" and not (p.get("context_key") or "").strip():
                issues.append(_err(
                    f"{path}.context_key",
                    "来源为「会话上下文」时必须指定要读取的会话变量名",
                    M,
                ))
            if src == "const" and (p.get("const_value") in (None, "")):
                issues.append(_err(
                    f"{path}.const_value", "来源为「固定值」时必须填写具体值", M,
                ))
            if p.get("required") and src == "const":
                issues.append(_info(
                    f"{path}.required",
                    "固定值参数无需标必填 —— 它总是有值",
                    M,
                ))
        else:
            # 出参：脱敏与写回校验
            if p.get("mask_rule") == "custom" and not (p.get("mask_pattern") or "").strip():
                issues.append(_err(
                    f"{path}.mask_pattern",
                    "脱敏规则为「自定义」时必须提供正则",
                    M,
                ))
            if p.get("mask_pattern"):
                try:
                    re.compile(p["mask_pattern"])
                except re.error as e:
                    issues.append(_err(f"{path}.mask_pattern", f"脱敏正则非法：{e}", M))
            if p.get("write_to_context") and not (p.get("context_write_key") or "").strip():
                issues.append(_err(
                    f"{path}.context_write_key",
                    "勾选了「写回会话上下文」但未指定变量名",
                    M,
                ))
            if p.get("filtered") and p.get("write_to_context"):
                issues.append(_info(
                    f"{path}.filtered",
                    "该字段不返回给模型，但会写入会话上下文供后续技能使用",
                    M,
                ))

    return issues


# ---------------------------------------------------------------------------
# 规则 14–15：编排流程（模块 3）
# ---------------------------------------------------------------------------

def validate_flow(
    nodes: Sequence[Dict[str, Any]],
    ref_lifecycles: Optional[Dict[int, str]] = None,
) -> List[SkillIssue]:
    """编排型技能的流程图校验：无环、连通、引用有效。"""
    issues: List[SkillIssue] = []
    M = "exec"
    if not nodes:
        return issues

    keys = [n.get("node_key") for n in nodes if n.get("node_key")]
    dup = {k for k in keys if keys.count(k) > 1}
    if dup:
        issues.append(_err("exec_flow.nodes", f"节点键重复：{'、'.join(sorted(dup))}", M))

    key_set = set(keys)
    starts = [n for n in nodes if n.get("node_type") == "start"]
    ends = [n for n in nodes if n.get("node_type") == "end"]

    if len(starts) != 1:
        issues.append(_err(
            "exec_flow.nodes",
            f"流程必须有且只有 1 个开始节点（当前 {len(starts)} 个）", M,
        ))
    if not ends:
        issues.append(_err("exec_flow.nodes", "流程必须至少有 1 个结束节点", M))

    # 后继引用有效性
    for n in nodes:
        nk = n.get("node_key")
        for nx in (n.get("next_keys") or []):
            if nx not in key_set:
                issues.append(_err(
                    f"exec_flow.{nk}.next_keys",
                    f"后继节点 '{nx}' 不存在", M,
                ))
        fail = n.get("on_fail_next")
        if fail and fail not in key_set:
            issues.append(_err(
                f"exec_flow.{nk}.on_fail_next", f"失败跳转节点 '{fail}' 不存在", M,
            ))
        if n.get("node_type") == "skill" and not n.get("ref_skill_id"):
            issues.append(_err(
                f"exec_flow.{nk}.ref_skill_id", "技能节点必须引用一个原子 Skill", M,
            ))
        if n.get("node_type") == "branch" and not (n.get("condition_expr") or "").strip():
            issues.append(_err(
                f"exec_flow.{nk}.condition_expr", "分支节点必须填写判断表达式", M,
            ))

    # ⑭ 环检测（DFS）
    graph = {n.get("node_key"): list(n.get("next_keys") or []) for n in nodes}
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {k: WHITE for k in graph}

    def has_cycle(u: str, trail: List[str]) -> Optional[List[str]]:
        color[u] = GRAY
        for v in graph.get(u, []):
            if v not in color:
                continue
            if color[v] == GRAY:
                return trail + [u, v]
            if color[v] == WHITE:
                got = has_cycle(v, trail + [u])
                if got:
                    return got
        color[u] = BLACK
        return None

    for k in list(graph.keys()):
        if color.get(k) == WHITE:
            cyc = has_cycle(k, [])
            if cyc:
                issues.append(_err(
                    "exec_flow.nodes",
                    f"流程存在环：{' → '.join(cyc)}。"
                    f"如需重复执行请用「循环」节点，不要用回边",
                    M,
                ))
                break

    # ⑭ 孤立节点 / 可达性
    if starts:
        reach = set()
        stack = [starts[0].get("node_key")]
        while stack:
            cur = stack.pop()
            if cur in reach or cur not in graph:
                continue
            reach.add(cur)
            stack.extend(graph.get(cur, []))
            n = next((x for x in nodes if x.get("node_key") == cur), None)
            if n and n.get("on_fail_next"):
                stack.append(n["on_fail_next"])
        orphans = key_set - reach
        if orphans:
            issues.append(_err(
                "exec_flow.nodes",
                f"以下节点从开始节点不可达（孤立）：{'、'.join(sorted(orphans))}",
                M,
            ))
        if ends and not any(e.get("node_key") in reach for e in ends):
            issues.append(_err(
                "exec_flow.nodes", "从开始节点无法到达任何结束节点", M,
            ))

    # ⑮ 引用了未上线的 Skill
    if ref_lifecycles:
        for n in nodes:
            rid = n.get("ref_skill_id")
            if rid and ref_lifecycles.get(rid) not in (None, "released"):
                issues.append(_warn(
                    f"exec_flow.{n.get('node_key')}.ref_skill_id",
                    f"引用的 Skill 当前状态是「{ref_lifecycles.get(rid)}」而非「正式」，"
                    f"本技能上线后可能调用失败",
                    M,
                ))

    return issues


# ---------------------------------------------------------------------------
# 策略校验（模块 4、5）
# ---------------------------------------------------------------------------

def validate_policy(policy: Optional[Dict[str, Any]]) -> List[SkillIssue]:
    issues: List[SkillIssue] = []
    if not policy:
        return issues
    M4, M5 = "policy", "security"

    if policy.get("fallback_mode") in ("static", "skill", "prompt"):
        if not (policy.get("fallback_payload") or "").strip():
            issues.append(_err(
                "policy.fallback_payload",
                f"降级方式为「{policy['fallback_mode']}」时必须提供兜底内容", M4,
            ))

    ct = policy.get("circuit_threshold")
    if ct is not None:
        if not policy.get("circuit_window_sec"):
            issues.append(_warn(
                "policy.circuit_window_sec", "配置了熔断阈值但未设统计窗口", M4,
            ))
        if (policy.get("circuit_min_calls") or 0) < 5:
            issues.append(_warn(
                "policy.circuit_min_calls",
                "最小样本数过小，低流量时可能因偶发失败误熔断（建议 ≥10）", M4,
            ))

    # 错误码映射
    for i, em in enumerate(policy.get("error_maps") or []):
        if not (em.get("match") or "").strip():
            issues.append(_err(f"policy.error_maps[{i}].match", "匹配条件不能为空", M4))
        if not (em.get("user_msg") or "").strip():
            issues.append(_err(
                f"policy.error_maps[{i}].user_msg",
                "必须提供给用户的友好话术 —— 否则用户会看到原始错误码", M4,
            ))

    # 黑白名单冲突
    wl = set(policy.get("account_whitelist") or [])
    bl = set(policy.get("account_blacklist") or [])
    both = wl & bl
    if both:
        issues.append(_err(
            "policy.account_blacklist",
            f"账号同时在黑白名单中：{'、'.join(sorted(both))}", M5,
        ))
    if wl:
        issues.append(_info(
            "policy.account_whitelist",
            f"白名单非空 → 仅这 {len(wl)} 个账号可调用该技能，其余全部拒绝", M5,
        ))

    if policy.get("require_confirm") and not (policy.get("confirm_prompt") or "").strip():
        issues.append(_warn(
            "policy.confirm_prompt",
            "开启了二次确认但未配置话术，用户会看到通用提示", M5,
        ))

    return issues


# ---------------------------------------------------------------------------
# 聚合入口
# ---------------------------------------------------------------------------

def validate_skill(data: Dict[str, Any]) -> SkillValidation:
    """全量校验。data 结构见 SkillFullResponse。"""
    issues: List[SkillIssue] = []

    meta = data.get("meta") or {}
    kind = meta.get("skill_kind") or "prompt"
    exec_api = data.get("exec_api")
    exec_prompt = data.get("exec_prompt")
    exec_flow = data.get("exec_flow") or {}
    policy = data.get("policy")
    params_in = data.get("params_in") or []
    params_out = data.get("params_out") or []

    issues.extend(validate_opencode_compliance(
        data.get("name") or "",
        data.get("description") or "",
        data.get("metadata_json"),
        data.get("files") or [],
        data.get("body"),
    ))
    issues.extend(validate_meta(meta, policy, params_out, exec_api))
    issues.extend(validate_params(params_in, "in"))
    issues.extend(validate_params(params_out, "out"))
    issues.extend(validate_secrets(exec_api))
    issues.extend(validate_policy(policy))

    # 形态与执行配置一致性
    if kind == "api":
        if not exec_api:
            issues.append(_err(
                "exec_api", "形态为「API 工具调用型」但未配置执行信息", "exec",
            ))
        elif not any([
            exec_api.get("url_test"), exec_api.get("url_staging"), exec_api.get("url_prod"),
        ]):
            issues.append(_err(
                "exec_api.url_test", "至少要配置一个环境的接口地址", "exec",
            ))
    elif kind == "prompt":
        if not exec_prompt or not (exec_prompt.get("system_prompt") or "").strip():
            issues.append(_warn(
                "exec_prompt.system_prompt",
                "形态为「Prompt 推理型」但未配置系统提示词，模型将无指导地推理",
                "exec",
            ))
    elif kind == "flow":
        nodes = exec_flow.get("nodes") or []
        if not nodes:
            issues.append(_err(
                "exec_flow.nodes", "形态为「可视化编排组合型」但未编排任何节点", "exec",
            ))
        issues.extend(validate_flow(nodes, data.get("ref_lifecycles")))

    # 双平面说明 —— 让用户明白治理配置为什么不在 SKILL.md 里
    gov_fields = [
        k for k, v in (
            ("限流 QPS", meta.get("qps_limit")),
            ("会话频次", meta.get("session_call_limit")),
            ("熔断", (policy or {}).get("circuit_threshold")),
            ("RBAC", (policy or {}).get("allowed_roles")),
            ("脱敏", any(p.get("mask_rule", "none") != "none" for p in params_out)),
        ) if v
    ]
    if gov_fields:
        issues.append(_info(
            "control_plane",
            f"已配置的治理项（{'、'.join(gov_fields)}）由平台网关执行，"
            f"不会写入 SKILL.md 顶层 —— OpenCode 不识别这些字段。"
            f"摘要会以 metadata.omd_* 导出，全量配置在 _ontomind/skill.manifest.json",
            "compliance",
        ))

    ok = not any(i.level == "error" for i in issues)
    return SkillValidation(ok=ok, issues=issues)


__all__ = [
    "detect_plaintext_secret",
    "validate_opencode_compliance",
    "validate_secrets",
    "validate_meta",
    "validate_lifecycle_transition",
    "validate_params",
    "validate_flow",
    "validate_policy",
    "validate_skill",
]
