"""Request-record analysis helpers."""

from __future__ import annotations

from collections import defaultdict
import csv
from pathlib import Path
from statistics import mean
from typing import Any, Iterable, Mapping

from .storage import read_jsonl, write_json


def per_agent_summary(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        buckets[str(row.get("agent_id") or "")].append(row)

    summaries = []
    for agent_id, agent_rows in sorted(buckets.items()):
        prompt_tokens = _sum(agent_rows, "prompt_tokens")
        cached_tokens = _sum(agent_rows, "cached_tokens")
        summaries.append(
            {
                "agent_id": agent_id,
                "request_count": len(agent_rows),
                "prompt_tokens": prompt_tokens,
                "cached_tokens": cached_tokens,
                "new_prefill_tokens": _sum(agent_rows, "new_prefill_tokens"),
                "workflow_weighted_hit_ratio": _ratio(cached_tokens, prompt_tokens),
                "mean_ttft_ms": _mean_present(agent_rows, "ttft_ms"),
                "mean_e2e_ms": _mean_present(agent_rows, "e2e_ms"),
            }
        )
    return summaries


def transition_summary(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        key = (str(row.get("previous_agent_id") or ""), str(row.get("agent_id") or ""))
        buckets[key].append(row)

    summaries = []
    for (previous_agent_id, agent_id), transition_rows in sorted(buckets.items()):
        prompt_tokens = _sum(transition_rows, "prompt_tokens")
        cached_tokens = _sum(transition_rows, "cached_tokens")
        summaries.append(
            {
                "previous_agent_id": previous_agent_id,
                "agent_id": agent_id,
                "request_count": len(transition_rows),
                "prompt_tokens": prompt_tokens,
                "cached_tokens": cached_tokens,
                "new_prefill_tokens": _sum(transition_rows, "new_prefill_tokens"),
                "workflow_weighted_hit_ratio": _ratio(cached_tokens, prompt_tokens),
                "mean_ttft_ms": _mean_present(transition_rows, "ttft_ms"),
                "mean_e2e_ms": _mean_present(transition_rows, "e2e_ms"),
            }
        )
    return summaries


def write_analysis_outputs(requests_jsonl: str | Path, output_dir: str | Path) -> dict[str, Path]:
    rows = read_jsonl(requests_jsonl)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    agent_rows = per_agent_summary(rows)
    transition_rows = transition_summary(rows)
    agent_json = output_path / "per_agent_summary.json"
    transition_json = output_path / "transition_summary.json"
    agent_csv = output_path / "per_agent_summary.csv"
    transition_csv = output_path / "transition_summary.csv"

    write_json(agent_json, agent_rows)
    write_json(transition_json, transition_rows)
    _write_csv(agent_csv, agent_rows)
    _write_csv(transition_csv, transition_rows)
    return {
        "per_agent_json": agent_json,
        "transition_json": transition_json,
        "per_agent_csv": agent_csv,
        "transition_csv": transition_csv,
    }


def _sum(rows: Iterable[Mapping[str, Any]], key: str) -> int:
    total = 0
    for row in rows:
        value = row.get(key)
        if value is None:
            continue
        total += int(value)
    return total


def _ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def _mean_present(rows: Iterable[Mapping[str, Any]], key: str) -> float | None:
    values = [float(row[key]) for row in rows if row.get(key) is not None]
    if not values:
        return None
    return mean(values)


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
