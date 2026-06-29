# MVP Implementation Notes

This implementation starts with Level 1 request-level profiling from
`agents.md`, using KVFlow as the baseline workflow.

## Implemented

- Baseline KVFlow order: `planner -> executor -> expresser -> reviewer -> planner or END`.
- Shared profiled SGLang client wrapper for every agent request.
- Stable request identifiers generated before sending requests.
- Canonical request rows in JSONL.
- Derived metrics:
  - `new_prefill_tokens = max(prompt_tokens - cached_tokens, 0)`
  - `reported_cache_hit_ratio = cached_tokens / prompt_tokens`
  - `e2e_ms = response_complete_time_ms - request_submitted_time_ms`
  - streaming `ttft_ms` and `tpot_ms` when first-token timing is available.
- Raw prompt artifacts with serialized prompt text and request metadata.
- Per-agent and transition-level summaries.
- Environment metadata capture.

## Required Integrations

- LangGraph is the required workflow runtime for production profiler runs.
- MLflow Tracing is required for LangGraph workflow observability.
- LangGraph invocations pass `thread_id` in config so MLflow can group traces
  into sessions.
- Future workflow variants may change graph topology and agent roles, but must
  keep the canonical request identifiers and tracing contract.
- Parquet export is enabled when `pandas` and `pyarrow` are installed.

## Validation Targets

The current tests cover schema calculation, request identifier completeness, and
workflow agent order. Live SGLang validation should add the cold request, exact
repeat, appended conversation, and one-token divergence experiments from
`agents.md`.
