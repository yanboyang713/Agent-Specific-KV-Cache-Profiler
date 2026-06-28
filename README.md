# Agent-Specific KV-Cache Profiler

Initial implementation of the KVFlow-style profiler described in `agents.md`.

The first slice focuses on request-level profiling:

- fixed agent identities: `planner`, `executor`, `expresser`, `reviewer`;
- one shared OpenAI-compatible SGLang client wrapper;
- generated `request_uuid` values before model calls;
- canonical JSONL records with cache and latency fields;
- optional Parquet export when `pandas` and `pyarrow` are installed;
- optional LangGraph and MLflow integration without making tests depend on them.

## Quick Start

Run a single KVFlow pass against an SGLang server:

```bash
python -m kv_cache_profiler.cli run \
  --prompt "Profile how this workflow reuses KV cache." \
  --sglang-url http://localhost:30000 \
  --model profiler-model \
  --requests-jsonl artifacts/requests.jsonl \
  --prompt-artifact-dir artifacts/prompts \
  --max-turns 1 \
  --stream
```

Generate summaries from captured request records:

```bash
python -m kv_cache_profiler.cli analyze \
  --requests-jsonl artifacts/requests.jsonl \
  --output-dir artifacts/analysis
```

Record environment metadata:

```bash
python -m kv_cache_profiler.cli record-env \
  --output artifacts/environment.json
```

## Notes

The core package uses only the Python standard library. Install optional extras
for production experiments:

```bash
pip install -e ".[langgraph,mlflow,analysis,dev]"
```

When `langgraph` is unavailable, the workflow runner uses a deterministic local
state-machine fallback with the same agent order and request metadata.
