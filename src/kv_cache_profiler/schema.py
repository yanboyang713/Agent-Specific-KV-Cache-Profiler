"""Canonical request schema and metric helpers."""

from __future__ import annotations

from dataclasses import dataclass, fields
import hashlib
import json
from typing import Any, Mapping, Sequence

CANONICAL_REQUEST_FIELDS = [
    "benchmark_run_id",
    "experiment_name",
    "workflow_id",
    "workflow_run_id",
    "workflow_type",
    "thread_id",
    "workflow_concurrency",
    "agent_id",
    "previous_agent_id",
    "turn_id",
    "graph_node",
    "request_uuid",
    "sglang_response_id",
    "model_name",
    "prompt_template_version",
    "chat_template_name",
    "prompt_hash",
    "token_id_hash",
    "prompt_tokens",
    "cached_tokens",
    "new_prefill_tokens",
    "reported_cache_hit_ratio",
    "output_tokens",
    "ttft_ms",
    "tpot_ms",
    "e2e_ms",
    "cache_used_tokens_before",
    "cache_used_tokens_after",
    "cache_utilization_before",
    "cache_utilization_after",
    "running_requests",
    "queued_requests",
    "timestamp_start_ns",
    "timestamp_end_ns",
    "status",
    "error_type",
]


def stable_json_dumps(value: Any) -> str:
    """Serialize JSON-compatible data deterministically."""

    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def serialize_messages(messages: Sequence[Mapping[str, Any]]) -> str:
    return stable_json_dumps(list(messages))


def hash_messages(messages: Sequence[Mapping[str, Any]]) -> str:
    return sha256_text(serialize_messages(messages))


def elapsed_ms(start_ns: int | None, end_ns: int | None) -> float | None:
    if start_ns is None or end_ns is None:
        return None
    if end_ns < start_ns:
        return None
    return (end_ns - start_ns) / 1_000_000


def safe_ratio(numerator: int | float, denominator: int | float) -> float:
    if denominator <= 0:
        return 0.0
    return float(numerator) / float(denominator)


@dataclass(slots=True)
class RequestRecord:
    benchmark_run_id: str = ""
    experiment_name: str = "agent-specific-kv-cache-profiling"
    workflow_id: str = "kvflow-peer"
    workflow_run_id: str = ""
    workflow_type: str = "kvflow-peer"
    thread_id: str = ""
    workflow_concurrency: int = 1
    agent_id: str = ""
    previous_agent_id: str = "START"
    turn_id: int = 1
    graph_node: str = ""
    request_uuid: str = ""
    sglang_response_id: str = ""
    model_name: str = ""
    prompt_template_version: str = "kvflow-v1"
    chat_template_name: str = "openai-chat-json"
    prompt_hash: str = ""
    token_id_hash: str = ""
    prompt_tokens: int = 0
    cached_tokens: int = 0
    new_prefill_tokens: int = 0
    reported_cache_hit_ratio: float = 0.0
    output_tokens: int = 0
    ttft_ms: float | None = None
    tpot_ms: float | None = None
    e2e_ms: float | None = None
    cache_used_tokens_before: int | None = None
    cache_used_tokens_after: int | None = None
    cache_utilization_before: float | None = None
    cache_utilization_after: float | None = None
    running_requests: int | None = None
    queued_requests: int | None = None
    timestamp_start_ns: int = 0
    timestamp_end_ns: int = 0
    status: str = "ok"
    error_type: str | None = None

    @classmethod
    def build(
        cls,
        *,
        prompt_tokens: int,
        cached_tokens: int,
        output_tokens: int,
        timestamp_start_ns: int,
        timestamp_end_ns: int,
        first_token_ns: int | None = None,
        last_token_ns: int | None = None,
        **kwargs: Any,
    ) -> "RequestRecord":
        prompt_tokens = max(int(prompt_tokens), 0)
        cached_tokens = max(int(cached_tokens), 0)
        if prompt_tokens:
            cached_tokens = min(cached_tokens, prompt_tokens)
        output_tokens = max(int(output_tokens), 0)
        new_prefill_tokens = max(prompt_tokens - cached_tokens, 0)
        ttft_ms = elapsed_ms(timestamp_start_ns, first_token_ns)
        tpot_ms = None
        if output_tokens > 1 and first_token_ns is not None and last_token_ns is not None:
            token_span_ms = elapsed_ms(first_token_ns, last_token_ns)
            if token_span_ms is not None:
                tpot_ms = token_span_ms / (output_tokens - 1)

        return cls(
            prompt_tokens=prompt_tokens,
            cached_tokens=cached_tokens,
            new_prefill_tokens=new_prefill_tokens,
            reported_cache_hit_ratio=safe_ratio(cached_tokens, prompt_tokens),
            output_tokens=output_tokens,
            ttft_ms=ttft_ms,
            tpot_ms=tpot_ms,
            e2e_ms=elapsed_ms(timestamp_start_ns, timestamp_end_ns),
            timestamp_start_ns=timestamp_start_ns,
            timestamp_end_ns=timestamp_end_ns,
            **kwargs,
        )

    def to_dict(self) -> dict[str, Any]:
        values = {field.name: getattr(self, field.name) for field in fields(self)}
        return {name: values.get(name) for name in CANONICAL_REQUEST_FIELDS}

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.workflow_id:
            errors.append("workflow_id is required")
        if not self.workflow_run_id:
            errors.append("workflow_run_id is required")
        if not self.agent_id:
            errors.append("agent_id is required")
        if not self.request_uuid:
            errors.append("request_uuid is required")
        if self.cached_tokens < 0:
            errors.append("cached_tokens must be non-negative")
        if self.prompt_tokens < 0:
            errors.append("prompt_tokens must be non-negative")
        if self.prompt_tokens and self.cached_tokens > self.prompt_tokens:
            errors.append("cached_tokens must not exceed prompt_tokens")
        expected_new_prefill = max(self.prompt_tokens - self.cached_tokens, 0)
        if self.new_prefill_tokens != expected_new_prefill:
            errors.append("new_prefill_tokens does not match prompt_tokens - cached_tokens")
        if self.ttft_ms is not None and self.e2e_ms is not None and self.ttft_ms > self.e2e_ms:
            errors.append("ttft_ms must not exceed e2e_ms")
        return errors
