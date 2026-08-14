"""Agent 工厂单元测试 —— 校验器 / 渲染器 / 往返一致性.

这些是「静默失效类」缺陷的防线：
OpenCode 对非法权限键不报错只忽略，所以校验器的每条规则都必须有测试守着。
"""
from app.schemas.agent_factory_schema import (
    AGENT_PRESETS,
    BUNDLE_PRESETS,
    GLOB_CAPABLE_KEYS,
    PERMISSION_KEYS,
    SKILL_PRESETS,
)
from app.services.agent_factory_service import AgentFactoryService
from app.services.agent_render_service import (
    render_agent_md,
    render_bundle_config,
    render_skill_files,
    render_skill_md,
)
from app.services.agent_validate_service import (
    validate_agent,
    validate_bundle,
    validate_skill,
)

_DESC = "一个用于单元测试的 agent，描述需要足够长以避免过短警告"
_SKILL_DESC = "一个用于单元测试的 skill，描述需要足够长以避免触发过短告警提示"


def _errors(result):
    return [i for i in result.issues if i.level == "error"]


def _fields(result, level=None):
    return {i.field for i in result.issues if level is None or i.level == level}


# ---------------------------------------------------------------------------
# 权限键白名单（最重要的一条：OpenCode 静默忽略非法键）
# ---------------------------------------------------------------------------

def test_permission_keys_count_is_15():
    assert len(PERMISSION_KEYS) == 15
    assert len(GLOB_CAPABLE_KEYS) == 10
    assert set(GLOB_CAPABLE_KEYS) <= set(PERMISSION_KEYS)


def test_illegal_permission_key_is_error_with_correction():
    r = validate_agent({
        "name": "x", "description": _DESC,
        "permission_json": {"write": "deny"},
    })
    assert not r.ok
    msg = _errors(r)[0].message
    # 必须告诉用户正确的键是什么
    assert "edit" in msg


def test_unknown_permission_key_lists_legal_keys():
    r = validate_agent({
        "name": "x", "description": _DESC,
        "permission_json": {"totally_bogus": "deny"},
    })
    assert not r.ok
    assert "15" in _errors(r)[0].message


def test_non_glob_key_with_object_is_error():
    """webfetch 只接受简写动作，给 object 必须报错。"""
    r = validate_agent({
        "name": "x", "description": _DESC,
        "permission_json": {"webfetch": {"*": "allow"}},
    })
    assert not r.ok
    assert "permission.webfetch" in _fields(r, "error")


def test_glob_key_with_object_is_ok():
    r = validate_agent({
        "name": "x", "description": _DESC,
        "permission_json": {"bash": {"*": "ask", "git diff": "allow"}},
    })
    assert r.ok


def test_star_not_first_is_warning():
    """OpenCode 最后匹配胜出，"*" 放中间会覆盖后面的规则。"""
    r = validate_agent({
        "name": "x", "description": _DESC,
        "permission_json": {"bash": {"git diff": "allow", "*": "ask", "ls": "allow"}},
    })
    assert r.ok  # 只是 warning，不阻断
    assert any(i.level == "warning" and "permission.bash" == i.field for i in r.issues)


def test_illegal_action_is_error():
    r = validate_agent({
        "name": "x", "description": _DESC,
        "permission_json": {"edit": "maybe"},
    })
    assert not r.ok


# ---------------------------------------------------------------------------
# Agent 其它字段
# ---------------------------------------------------------------------------

def test_agent_name_pattern():
    for bad in ("Bad-Name", "bad--name", "-bad", "bad-", "bad_name", ""):
        r = validate_agent({"name": bad, "description": _DESC})
        assert not r.ok, f"{bad!r} 应该被拒绝"
    r = validate_agent({"name": "code-reviewer", "description": _DESC})
    assert r.ok


def test_agent_description_required_and_capped():
    assert not validate_agent({"name": "x", "description": ""}).ok
    assert not validate_agent({"name": "x", "description": "a" * 1025}).ok


def test_agent_color_validation():
    assert not validate_agent({"name": "x", "description": _DESC, "color": "blue"}).ok
    assert validate_agent({"name": "x", "description": _DESC, "color": "#3b52af"}).ok
    assert validate_agent({"name": "x", "description": _DESC, "color": "accent"}).ok


def test_agent_dangerous_combo_is_warning():
    r = validate_agent({
        "name": "x", "description": _DESC,
        "permission_json": {"edit": "allow", "bash": "allow"},
    })
    assert r.ok
    assert any(i.level == "warning" and i.field == "permission" for i in r.issues)


# ---------------------------------------------------------------------------
# Skill
# ---------------------------------------------------------------------------

def test_skill_path_traversal_blocked():
    for bad in ("../evil.md", "/etc/passwd", "a/../../b.md"):
        r = validate_skill({
            "name": "s", "description": _SKILL_DESC, "body": "# x",
            "files": [{"rel_path": bad, "content": "x"}],
        })
        assert not r.ok, f"{bad!r} 应该被拒绝"


def test_skill_file_cannot_shadow_skill_md():
    r = validate_skill({
        "name": "s", "description": _SKILL_DESC, "body": "# x",
        "files": [{"rel_path": "SKILL.md", "content": "x"}],
    })
    assert not r.ok


def test_skill_duplicate_paths_blocked():
    r = validate_skill({
        "name": "s", "description": _SKILL_DESC, "body": "# x",
        "files": [
            {"rel_path": "a.md", "content": "1"},
            {"rel_path": "a.md", "content": "2"},
        ],
    })
    assert not r.ok


def test_skill_metadata_must_be_string_map():
    r = validate_skill({
        "name": "s", "description": _SKILL_DESC, "body": "# x",
        "metadata_json": {"n": 123},
    })
    assert not r.ok


def test_skill_multifile_ok():
    r = validate_skill({
        "name": "git-release", "description": _SKILL_DESC, "body": "# x",
        "files": [
            {"rel_path": "references/x.md", "content": "# x"},
            {"rel_path": "scripts/run.py", "content": "print(1)", "is_executable": True},
        ],
    })
    assert r.ok


# ---------------------------------------------------------------------------
# Bundle 拓扑一致性（Loop 能不能真正跑起来）
# ---------------------------------------------------------------------------

def test_bundle_requires_an_entry_point():
    """既没有自定义 primary、也没指定内置 build/plan 作入口 → 报错。"""
    r = validate_bundle(
        {"name": "b", "subagent_depth": 1},
        [{"name": "rev", "mode": "subagent"}],
        [],
    )
    assert not r.ok


def test_bundle_may_rely_on_builtin_primary():
    """只自定义 subagent、主对话用 OpenCode 内置 build/plan 是**合法**用法。

    回归保护：内置预设「先规划后执行」「实现与评审环」「单体全能」都是这种形态，
    早期实现把它误判为 error，导致这些预设在页面上全部报「没有 primary agent」。
    """
    for builtin in ("build", "plan"):
        r = validate_bundle(
            {"name": "b", "default_agent": builtin, "subagent_depth": 1},
            [{"name": "code-reviewer", "mode": "subagent"}],
            [],
        )
        assert r.ok, f"default_agent={builtin} 应被接受"
        # 应给出 info 级说明，而不是 error/warning
        assert any(i.level == "info" and i.field == "members" for i in r.issues)
        assert not _errors(r)


def test_bundle_with_no_members_but_builtin_entry_is_ok():
    """「单体全能」形态：零成员 + 内置 build 作入口。"""
    r = validate_bundle(
        {"name": "单体全能", "default_agent": "build", "subagent_depth": 0}, [], [],
    )
    assert r.ok
    assert not _errors(r)


def test_bundle_default_agent_must_be_primary():
    r = validate_bundle(
        {"name": "b", "default_agent": "rev", "subagent_depth": 1},
        [
            {"name": "orc", "mode": "primary"},
            {"name": "rev", "mode": "subagent"},
        ],
        [],
    )
    assert not r.ok
    assert "default_agent" in _fields(r, "error")


def test_bundle_depth_zero_with_subagents_warns():
    r = validate_bundle(
        {"name": "b", "subagent_depth": 0},
        [
            {"name": "orc", "mode": "primary"},
            {"name": "rev", "mode": "subagent"},
        ],
        [],
    )
    assert r.ok
    assert "subagent_depth" in _fields(r, "warning")


def test_bundle_dead_task_reference_warns():
    """permission.task 指向不存在的 subagent → 规则不会生效。"""
    r = validate_bundle(
        {"name": "b", "subagent_depth": 1},
        [{
            "name": "orc", "mode": "primary",
            "permission_json": {"task": {"*": "deny", "ghost": "allow"}},
        }],
        [],
    )
    assert any("ghost" in i.message for i in r.issues)


def test_bundle_duplicate_agent_is_error():
    r = validate_bundle(
        {"name": "b", "subagent_depth": 1},
        [
            {"name": "orc", "mode": "primary"},
            {"name": "orc", "mode": "subagent"},
        ],
        [],
    )
    assert not r.ok


# ---------------------------------------------------------------------------
# 渲染器
# ---------------------------------------------------------------------------

def test_render_agent_quotes_glob_keys():
    """glob 键含空格/星号必须加引号，否则 OpenCode 的 YAML 解析不稳定。"""
    md = render_agent_md({
        "name": "x", "description": "测试", "mode": "subagent",
        "permission_json": {"bash": {"*": "ask", "git diff": "allow"}},
    })
    assert '"*": ask' in md
    assert '"git diff": allow' in md


def test_render_agent_keeps_chinese_unescaped():
    md = render_agent_md({"name": "x", "description": "中文描述", "mode": "subagent"})
    assert "中文描述" in md
    assert "\\u" not in md


def test_render_agent_omits_empty_fields():
    """空值不应写进 frontmatter，交给 OpenCode 用默认行为。"""
    md = render_agent_md({"name": "x", "description": "d", "mode": "subagent"})
    assert "temperature" not in md
    assert "color" not in md
    assert "null" not in md


def test_render_agent_quotes_hex_color():
    md = render_agent_md({
        "name": "x", "description": "d", "mode": "subagent", "color": "#3b52af",
    })
    # # 开头在 YAML 里是注释，必须加引号
    assert 'color: "#3b52af"' in md


def test_render_skill_only_emits_legal_frontmatter():
    """OpenCode 只认 5 个字段，多写的会被忽略、反而误导维护者。"""
    md = render_skill_md({
        "name": "s", "description": "d", "license": "MIT",
        "compatibility": "opencode", "metadata_json": {"a": "b"},
        "category": "should-not-appear", "display_name": "no",
    })
    assert "category" not in md
    assert "display_name" not in md
    assert "license: MIT" in md


def test_render_skill_dir_matches_name():
    """目录名必须等于 name，否则 OpenCode 不加载。"""
    arts = render_skill_files({
        "name": "my-skill", "description": "d", "body": "# x",
        "files": [{"rel_path": "references/a.md", "content": "# a"}],
    })
    paths = {a.path for a in arts}
    assert "skills/my-skill/SKILL.md" in paths
    assert "skills/my-skill/references/a.md" in paths


def test_render_bundle_config_star_first_in_skill_rule():
    cfg = render_bundle_config(
        {"name": "b", "default_agent": "build", "subagent_depth": 1},
        [{"name": "orc"}],
        [{"name": "sk"}],
        {"sk": "allow"},
    )
    import json as _json

    body = cfg[cfg.index("{"):]
    data = _json.loads(body)
    rule = data["permission"]["skill"]
    assert list(rule.keys())[0] == "*", "OpenCode 最后匹配胜出，* 必须在最前"


# ---------------------------------------------------------------------------
# 往返一致性（渲染 → 解析）
# ---------------------------------------------------------------------------

def test_agent_md_roundtrip_preserves_all_fields():
    """渲染出的 .md 再解析回来，关键字段必须完全一致 —— 导入功能的正确性基础。"""
    original = {
        "name": "code-reviewer",
        "description": "审查代码的正确性与安全性，只读不改",
        "mode": "subagent",
        "temperature": 0.15,
        "color": "#3b52af",
        "steps": 20,
        "permission_json": {
            "edit": "deny",
            "bash": {"*": "ask", "git diff": "allow", "git log*": "allow"},
            "read": "allow",
        },
    }
    md = render_agent_md(original)
    parsed = AgentFactoryService._parse_agent_md(md)
    for field in ("description", "mode", "temperature", "color", "steps"):
        assert parsed.get(field) == original[field], f"{field} 往返不一致"
    assert parsed.get("permission_json") == original["permission_json"]


def test_agent_md_roundtrip_for_all_presets():
    """所有内置预设都必须能无损往返。"""
    for p in AGENT_PRESETS:
        d = dict(p)
        d["permission_json"] = d.pop("permission", None)
        md = render_agent_md(d)
        parsed = AgentFactoryService._parse_agent_md(md)
        assert parsed.get("permission_json") == d["permission_json"], (
            f"{p['name']} 权限往返不一致"
        )
        assert parsed.get("mode") == d.get("mode"), f"{p['name']} mode 往返不一致"


# ---------------------------------------------------------------------------
# 预设自身合法性（预设是用户的学习范本，自己必须是对的）
# ---------------------------------------------------------------------------

def test_all_agent_presets_are_valid():
    for p in AGENT_PRESETS:
        d = dict(p)
        d["permission_json"] = d.pop("permission", None)
        r = validate_agent(d)
        assert r.ok, f"预设 {p['name']} 校验失败: {[i.message for i in _errors(r)]}"


def test_all_skill_presets_are_valid():
    for p in SKILL_PRESETS:
        r = validate_skill(p)
        assert r.ok, f"预设 {p['name']} 校验失败: {[i.message for i in _errors(r)]}"


def test_all_bundle_presets_reference_existing_members():
    agent_names = {a["name"] for a in AGENT_PRESETS}
    skill_names = {s["name"] for s in SKILL_PRESETS}
    for b in BUNDLE_PRESETS:
        for name, _ in b.get("agents") or []:
            assert name in agent_names, f"{b['name']} 引用了不存在的 agent {name}"
        for name, _ in b.get("skills") or []:
            assert name in skill_names, f"{b['name']} 引用了不存在的 skill {name}"


def test_all_bundle_presets_pass_validation():
    """内置 bundle 预设本身必须校验通过 —— 它们是用户的学习范本。

    回归保护：曾因「必须有 primary 成员」的误判导致 6 个预设中 3 个报错。
    """
    from app.services.agent_validate_service import validate_bundle as vb

    agent_by_name = {a["name"]: a for a in AGENT_PRESETS}
    for b in BUNDLE_PRESETS:
        agents = []
        for name, role in b.get("agents") or []:
            src = dict(agent_by_name[name])
            src["permission_json"] = src.pop("permission", None)
            # bundle 里的 role 覆盖模板自身的 mode（与 service 层一致）
            src["mode"] = role
            agents.append(src)
        skills = [{"name": n} for n, _ in (b.get("skills") or [])]
        r = vb(
            {
                "name": b["name"],
                "pattern": b["pattern"],
                "default_agent": b.get("default_agent"),
                "subagent_depth": b.get("subagent_depth"),
                "global_permission_json": b.get("global_permission_json"),
            },
            agents,
            skills,
        )
        errs = [i for i in r.issues if i.level == "error"]
        assert r.ok, f"预设「{b['name']}」校验失败: {[i.message for i in errs]}"


# ---------------------------------------------------------------------------
# 性能相关的结构性保护
# ---------------------------------------------------------------------------

def test_container_cache_helpers_respect_ttl():
    """短 TTL 缓存必须真的会过期 —— 否则容器状态会永久读旧值。"""
    import time as _t

    from app.services import compute_service as cs

    store: dict = {}
    cs._cache_put(store, "k", "v", 0.05)
    assert cs._cache_get(store, "k") == "v"
    _t.sleep(0.08)
    assert cs._cache_get(store, "k") is None, "TTL 到期后必须失效"


def test_invalidate_container_cache_clears_entries():
    """容器增删启停后必须能清掉缓存，否则前端看到的是旧状态。"""
    from app.services import compute_service as cs

    cs._cache_put(cs._containers_cache, (1, True), ["x"], 60)
    cs._cache_put(cs._listen_cache, (1, "abc"), {4096: "0.0.0.0"}, 60)
    cs._cache_put(cs._containers_cache, (2, True), ["y"], 60)

    cs.invalidate_container_cache(1)
    assert cs._cache_get(cs._containers_cache, (1, True)) is None
    assert cs._cache_get(cs._listen_cache, (1, "abc")) is None
    # 只清指定节点，别的节点不受影响
    assert cs._cache_get(cs._containers_cache, (2, True)) == ["y"]

    cs.invalidate_container_cache()
    assert cs._cache_get(cs._containers_cache, (2, True)) is None


def test_discover_services_skips_offline_nodes_by_default():
    """离线远程节点必须默认跳过。

    回归保护：SSH 连不通要等 ~10s 超时，之前 AIDE 首屏/轮询因此整体卡 10s+。
    """
    import inspect

    from app.services.compute_service import ComputeService

    src = inspect.getsource(ComputeService.discover_services)
    assert "include_offline" in src, "必须支持跳过离线节点"
    assert "asyncio.wait_for" in src, "每个节点必须有硬超时，避免坏节点拖垮整次扫描"


# ---------------------------------------------------------------------------
# task 权限归属：方案级覆盖，不污染 agent 模板
# ---------------------------------------------------------------------------

def test_synthesize_task_drops_rules_outside_bundle():
    """模板里指向方案外 agent 的规则必须被剔除。

    回归保护：早期把模板 task 原样写进产物，导致「规则指向 'docs-writer'，
    但它既不在本方案成员中…该规则不会生效」这类噪音 warning 刷屏。
    """
    from app.services.agent_render_service import synthesize_task_rule

    primary = {
        "name": "orchestrator",
        "permission_json": {
            "task": {
                "*": "deny",
                "explorer": "allow",
                "docs-writer": "allow",      # 本方案没有这个成员
                "security-auditor": "allow",  # 也没有
            }
        },
    }
    out = synthesize_task_rule(primary, ["explorer"])
    assert out == {"*": "deny", "explorer": "allow"}
    assert "docs-writer" not in out
    assert "security-auditor" not in out


def test_synthesize_task_bundle_override_wins():
    """方案内覆盖优先于模板规则。"""
    from app.services.agent_render_service import synthesize_task_rule

    primary = {"name": "orc", "permission_json": {"task": {"*": "deny"}}}
    # 模板里 docs-writer 命中 "*": deny，但方案里显式授权
    out = synthesize_task_rule(primary, ["docs-writer"], {"docs-writer": "allow"})
    assert out["docs-writer"] == "allow"
    assert out["*"] == "deny"


def test_synthesize_task_keeps_star_first():
    """OpenCode 最后匹配胜出 → "*" 必须是第一个 key。"""
    from app.services.agent_render_service import synthesize_task_rule

    primary = {"name": "orc", "permission_json": {"task": {"a": "allow", "*": "deny"}}}
    out = synthesize_task_rule(primary, ["a", "b"], {"b": "ask"})
    assert list(out.keys())[0] == "*"


def test_resolve_task_action_last_match_wins():
    """glob 解析必须与 OpenCode 语义一致：最后匹配胜出。"""
    from app.services.agent_render_service import resolve_task_action

    rule = {"*": "deny", "worker-*": "allow", "worker-bad": "deny"}
    assert resolve_task_action(rule, "other") == "deny"
    assert resolve_task_action(rule, "worker-a") == "allow"
    assert resolve_task_action(rule, "worker-bad") == "deny"
    # 未配置 = 默认 allow
    assert resolve_task_action(None, "x") == "allow"
    # 简写动作
    assert resolve_task_action("ask", "x") == "ask"


def test_outside_bundle_task_rules_are_info_not_warning():
    """模板有方案外规则时只给 info（渲染会剔除），不该报 warning。"""
    r = validate_bundle(
        {"name": "b", "default_agent": "orc", "subagent_depth": 1},
        [
            {
                "name": "orc",
                "mode": "primary",
                "permission_json": {"task": {"*": "deny", "ghost": "allow"}},
            },
            {"name": "explorer", "mode": "subagent"},
        ],
        [],
    )
    assert r.ok
    assert not [i for i in r.issues if i.level == "warning" and "ghost" in i.message]
    assert [i for i in r.issues if i.level == "info" and "ghost" in i.message]
