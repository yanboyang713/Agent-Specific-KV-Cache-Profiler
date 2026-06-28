"""Reproducible environment metadata capture."""

from __future__ import annotations

import os
import platform
import subprocess
import sys
from typing import Any


def collect_environment() -> dict[str, Any]:
    return {
        "operating_system": platform.platform(),
        "python_version": sys.version,
        "cuda_version": _command_output(["nvcc", "--version"]),
        "gpu": _command_output(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total,driver_version",
                "--format=csv,noheader",
            ]
        ),
        "pytorch_version": _package_version("torch"),
        "sglang_version": _package_version("sglang"),
        "langgraph_version": _package_version("langgraph"),
        "langchain_version": _package_version("langchain"),
        "mlflow_version": _package_version("mlflow"),
        "git_commit": _command_output(["git", "rev-parse", "HEAD"]),
        "model_identifier": os.environ.get("MODEL_PATH") or os.environ.get("MODEL_ID"),
    }


def _package_version(package_name: str) -> str | None:
    try:
        from importlib.metadata import version
    except ImportError:  # pragma: no cover - Python 3.10+ always has this
        return None
    try:
        return version(package_name)
    except Exception:
        return None


def _command_output(command: list[str]) -> str | None:
    try:
        completed = subprocess.run(command, capture_output=True, check=False, text=True, timeout=10)
    except Exception:
        return None
    output = (completed.stdout or completed.stderr).strip()
    return output or None
