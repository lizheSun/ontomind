"""插件注册表。内置 OpenCode / DSH；测试可整体替换。"""
from __future__ import annotations

from typing import Optional

from app.harness.protocol import PluginInfo, RunnerPlugin


class PluginRegistry:
    def __init__(self) -> None:
        self._plugins: dict[str, RunnerPlugin] = {}

    def register(self, plugin: RunnerPlugin) -> None:
        self._plugins[plugin.id] = plugin

    def get(self, plugin_id: str) -> Optional[RunnerPlugin]:
        return self._plugins.get(plugin_id)

    def list_info(self) -> list[PluginInfo]:
        return [p.probe() for p in self._plugins.values()]

    @classmethod
    def with_builtins(cls) -> "PluginRegistry":
        from app.harness.plugins.dsh import DshPlugin
        from app.harness.plugins.opencode import OpenCodePlugin

        reg = cls()
        reg.register(OpenCodePlugin())
        reg.register(DshPlugin())
        return reg


_REGISTRY: Optional[PluginRegistry] = None


def get_registry() -> PluginRegistry:
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = PluginRegistry.with_builtins()
    return _REGISTRY


def set_registry(reg: Optional[PluginRegistry]) -> None:
    global _REGISTRY
    _REGISTRY = reg
