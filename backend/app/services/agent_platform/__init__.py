"""Agent Platform services, imported lazily to keep optional connectors isolated."""

__all__ = [
    "DiscoveryService",
    "NodeService",
    "AgentService",
    "VersionService",
    "DeploymentService",
    "SessionService",
    "RunService",
    "ApprovalService",
]


def __getattr__(name):
    modules = {
        "DiscoveryService": "discovery_service",
        "NodeService": "node_service",
        "AgentService": "agent",
        "VersionService": "version",
        "DeploymentService": "deployment",
        "SessionService": "session",
        "RunService": "run",
        "ApprovalService": "approval",
    }
    module_name = modules.get(name)
    if module_name is None:
        raise AttributeError(name)
    from importlib import import_module

    return getattr(import_module(f"{__name__}.{module_name}"), name)
