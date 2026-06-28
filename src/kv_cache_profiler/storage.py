"""Artifact writers and readers."""

from __future__ import annotations

import json
from pathlib import Path
import threading
from typing import Any, Iterable, Mapping, Sequence

from .schema import RequestRecord, serialize_messages


class JSONLRequestWriter:
    """Append canonical request records to JSONL."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def append(self, record: RequestRecord) -> None:
        with self._lock:
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record.to_dict(), sort_keys=True) + "\n")


class PromptArtifactWriter:
    """Write raw request prompts as one JSON artifact per request."""

    def __init__(self, directory: str | Path) -> None:
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)

    def write(
        self,
        *,
        request_uuid: str,
        metadata: Mapping[str, Any],
        messages: Sequence[Mapping[str, Any]],
        serialized_prompt: str | None = None,
    ) -> Path:
        path = self.directory / f"{request_uuid}.json"
        payload = {
            "contains_raw_prompts": True,
            "contains_raw_outputs": False,
            "raw_prompt_logging": "enabled",
            "request_uuid": request_uuid,
            "metadata": dict(metadata),
            "messages": list(messages),
            "serialized_prompt": serialized_prompt or serialize_messages(messages),
        }
        with path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
        return path


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_json(path: str | Path, payload: Any) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def write_jsonl(path: str | Path, rows: Iterable[Mapping[str, Any]]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(dict(row), sort_keys=True) + "\n")


def export_jsonl_to_parquet(jsonl_path: str | Path, parquet_path: str | Path) -> None:
    try:
        import pandas as pd
    except ImportError as exc:  # pragma: no cover - depends on optional extras
        raise RuntimeError("Install the analysis extra to export Parquet: pandas and pyarrow") from exc

    output_path = Path(parquet_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    dataframe = pd.read_json(jsonl_path, lines=True)
    dataframe.to_parquet(output_path, index=False)
