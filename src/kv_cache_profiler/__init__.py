"""Agent-specific KV-cache profiler."""

from .client import ModelParameters, ProfiledChatResult, ProfiledSGLangClient, RequestContext
from .schema import CANONICAL_REQUEST_FIELDS, RequestRecord

__all__ = [
    "CANONICAL_REQUEST_FIELDS",
    "KVFLOW_AGENTS",
    "KVFlowConfig",
    "ModelParameters",
    "ProfiledChatResult",
    "ProfiledSGLangClient",
    "RequestContext",
    "RequestRecord",
    "run_kvflow",
]


def __getattr__(name: str):
    if name in {"KVFLOW_AGENTS", "KVFlowConfig", "run_kvflow"}:
        from . import workflow

        return getattr(workflow, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
