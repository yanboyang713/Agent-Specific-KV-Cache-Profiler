# Agent Instructions: Agent-Specific KV-Cache Profiler

This repository builds an agent-specific KV-cache profiler for a KVFlow-style multi-agent workflow using LangGraph, SGLang, and MLflow.

The first goal is characterization, not cache-policy optimization. Before adding workflow-aware eviction, prefetching, compression, or RL-based cache management, the system must accurately measure how agents use and reuse the KV cache.

## Project Objective

Build a profiler that can answer, for every LLM invocation:
- which workflow, turn, and agent issued the request;
- how many prompt tokens were submitted;
- how many prompt tokens were served from prefix cache;
- how many prompt tokens required new prefill computation;
- what the TTFT, TPOT, and end-to-end latency were;
- what the preceding agent transition was;
- what the approximate SGLang cache state was;
- whether the result can be reproduced from the recorded configuration.

The advanced version should also answer:

- which cache nodes were matched, inserted, accessed, retained, or evicted;
- whether reuse came from the same agent, another agent, or another workflow;
- how long useful prefixes remained resident;
- how cache behavior could influence future RL-based KV management decisions.

## Required Workflow

Use the KVFlow / PEER-style workflow exactly. Do not replace it with the generic Planner, Executor, Verifier workflow.

The workflow is:

```text
Planner -> Executor -> Expresser -> Reviewer -> Planner
```

Agent roles:

- `planner`: decomposes the problem, decides the next step, and updates the plan after review feedback.
- `executor`: performs the planned work, including tool calls, retrieval, reasoning, or synthesis needed for the current step.
- `expresser`: converts the executor's result into a clear user-facing answer, report, or intermediate response.
- `reviewer`: evaluates the expressed result, checks quality or completeness, and sends feedback back to the planner.

All implementation, tests, analysis, dashboards, and documentation should use these four agent identities unless a new experiment explicitly defines another KVFlow-compatible variant.

## Architecture

The profiler joins three layers.

```text
LangGraph application
  knows workflow, agent, transition, turn, graph state
        |
        | OpenAI-compatible request with correlation metadata
        v
SGLang server
  knows tokenization, prefix lookup, prefill, decode, cache behavior
        |
        | usage records, metrics, logs, optional cache events
        v
MLflow
  stores traces, spans, parameters, metrics, artifacts, comparisons
```

No single component has the complete view:

- LangGraph supplies workflow semantics.
- SGLang supplies serving and KV-cache telemetry.
- MLflow stores, correlates, visualizes, and compares measurements.

## Implementation Levels

### Level 1: Request-Level Profiling

Implement this first without modifying SGLang.

Collect for every inference request:

- `workflow_id`;
- `workflow_run_id`;
- `thread_id`;
- `agent_id`;
- `previous_agent_id`;
- `turn_id`;
- `request_uuid` or `agent_call_id`;
- `prompt_tokens`;
- `cached_tokens`;
- `new_prefill_tokens`;
- `reported_cache_hit_ratio`;
- `output_tokens`;
- `ttft_ms`;
- `tpot_ms`;
- `e2e_ms`;
- status and error information.

This level should be enough to compare per-agent cache reuse and agent-transition behavior.

### Level 2: Server-State Correlation

Add SGLang server metrics:

- global cache-hit rate;
- used cache tokens;
- cache utilization;
- running requests;
- queued requests;
- prompt throughput;
- generation throughput;
- TTFT and latency distributions.

Treat server-level metrics as contextual observations. Under concurrency, a before-and-after change in global cache state must not be attributed to one request without source-level evidence.

### Level 3: Source-Level Cache Instrumentation

Add this only after Level 1 and Level 2 are validated.

Useful event types:

- `prefix_match`;
- `prefix_insert`;
- `cache_access`;
- `cache_lock`;
- `cache_unlock`;
- `cache_evict`;
- `cache_offload`;
- `cache_prefetch_start`;
- `cache_prefetch_complete`.

Do not assign one permanent owner to a shared radix-tree node. Store event history instead: creator, accessors, timestamps, request IDs, agent IDs, workflow IDs, residency time, and reuse distance.

## Identifier Model

Use stable identifiers everywhere. Agent names alone are not globally unique.

Required hierarchy:

```text
thread_id
  workflow_run_id
    turn_id
      agent_id
        request_uuid
```

Identifier meanings:

- `benchmark_run_id`: one benchmark configuration or experiment condition.
- `thread_id`: persistent workflow session or conversation.
- `workflow_run_id`: one graph invocation or resumed execution.
- `agent_id`: one of `planner`, `executor`, `expresser`, `reviewer`.
- `previous_agent_id`: previous logical agent, or `START`.
- `turn_id`: logical workflow iteration.
- `request_uuid`: application-generated join key for MLflow, request logs, SGLang telemetry, and future cache events.

Propagate identifiers through:

- LangGraph state;
- MLflow span attributes;
- OpenAI-compatible SGLang request metadata or headers;
- canonical request records;
- SGLang logs and future cache-event records.

## MLflow Data Model

Use MLflow concepts consistently:

- Experiment: the full project, for example `agent-specific-kv-cache-profiling`.
- Run: one benchmark configuration.
- Trace: one complete workflow execution.
- Span: one workflow stage, agent invocation, model request, tool call, or
  cache event.

Expected span structure:

```text
workflow:<workflow_run_id>
  agent:planner
    sglang:chat-completion
  agent:executor
    tool:<tool-name>
    sglang:chat-completion
  agent:expresser
    sglang:chat-completion
  agent:reviewer
    sglang:chat-completion
```

Each SGLang inference span should include:

- `benchmark.run_id`;
- `workflow.id`;
- `workflow.run_id`;
- `thread.id`;
- `agent.id`;
- `agent.previous_id`;
- `agent.turn_id`;
- `request.uuid`;
- `request.sglang_response_id`;
- `model.name`;
- `model.temperature`;
- `model.max_tokens`;
- `prompt.template_version`;
- `prompt.hash`;
- `prompt.tokens`;
- `prompt.cached_tokens`;
- `prompt.new_prefill_tokens`;
- `prompt.reported_cache_hit_ratio`;
- `output.tokens`;
- `latency.ttft_ms`;
- `latency.tpot_ms`;
- `latency.e2e_ms`;
- server-state snapshots when available.

## Canonical Request Dataset

MLflow traces are useful for visualization, but statistical analysis should use one canonical row per model invocation.

Recommended fields:

```text
benchmark_run_id
experiment_name
workflow_id
workflow_run_id
workflow_type
thread_id
workflow_concurrency
agent_id
previous_agent_id
turn_id
graph_node
request_uuid
sglang_response_id
model_name
prompt_template_version
chat_template_name
prompt_hash
token_id_hash
prompt_tokens
cached_tokens
new_prefill_tokens
reported_cache_hit_ratio
output_tokens
ttft_ms
tpot_ms
e2e_ms
cache_used_tokens_before
cache_used_tokens_after
cache_utilization_before
cache_utilization_after
running_requests
queued_requests
timestamp_start_ns
timestamp_end_ns
status
error_type
```

Store the final table as Parquet. JSONL is acceptable for append-only raw event capture during development.

## Metric Definitions

Use plain org/Markdown-readable formulas in documentation. Avoid LaTeX unless the target document explicitly requires it.

```text
new_prefill_tokens = max(prompt_tokens - cached_tokens, 0)
```

```text
reported_cache_hit_ratio = cached_tokens / prompt_tokens
```

Name this metric `reported_cache_hit_ratio` because cache alignment and engine-specific accounting may affect the exact denominator.

```text
workflow_weighted_hit_ratio =
    sum(cached_tokens for all requests)
    /
    sum(prompt_tokens for all requests)
```

Use the weighted hit ratio instead of a simple average when comparing workflow runs. A ten-token request and a ten-thousand-token request should not have equal weight.

```text
recompute_burden =
    sum(new_prefill_tokens for all requests)
```

This estimates the amount of prompt work that could not be reused from cache. It often correlates more directly with workflow latency than average hit ratio.

```text
ttft_ms = first_token_time_ms - request_submitted_time_ms
```

```text
tpot_ms =
    (last_token_time_ms - first_token_time_ms)
    /
    (output_tokens - 1)
```

Only calculate TPOT when `output_tokens > 1`.

```text
e2e_latency_ms = response_complete_time_ms - request_submitted_time_ms
```

```text
cache_pressure = used_cache_tokens / cache_capacity_tokens
```

Prefer SGLang logical cache metrics over raw GPU memory. SGLang may reserve GPU memory at startup even when logical cache occupancy is low.

## Prompt Instrumentation

Prompt layout is a first-class experimental variable because prefix caching depends on exact token-prefix identity, not semantic similarity.

Record:

- raw application messages;
- serialized prompt text sent to the model;
- raw prompt text;
- token IDs;
- prompt template version;
- chat template name;
- prompt text hash;
- token ID hash;
- fixed prefix token count;
- dynamic suffix token count;
- first divergence token index between compared prompts.

Prompt decomposition:

```text
agent_prompt =
    shared_context
    + agent_role
    + fixed_examples
    + dynamic_state
    + current_input
```

Cache-friendly layout:

```text
shared_context
fixed_examples
agent_role
dynamic_state
current_input
```

Less cache-friendly layout:

```text
agent_role
shared_context
fixed_examples
dynamic_state
current_input
```

Store raw production prompts in this project. Also mark artifacts clearly with:

```text
contains_raw_prompts = true
contains_raw_outputs = true or false
raw_prompt_logging = enabled
```

## Required Development Phases

### Phase 0: Reproducible Environment

Record:

- operating system;
- Python version;
- CUDA version;
- GPU model and memory;
- NVIDIA driver;
- PyTorch version;
- SGLang commit or package version;
- LangGraph version;
- LangChain version;
- MLflow version;
- model identifier and revision;
- tokenizer revision;
- model precision;
- KV-cache precision;
- maximum context length;
- chat template;
- SGLang launch arguments.

### Phase 1: Start MLflow and SGLang

MLflow:

```bash
mlflow server \
  --host 0.0.0.0 \
  --port 5000
```

SGLang:

```bash
python -m sglang.launch_server \
  --model-path "$MODEL_PATH" \
  --served-model-name profiler-model \
  --host 0.0.0.0 \
  --port 30000 \
  --enable-cache-report \
  --enable-metrics \
  --log-requests \
  --log-requests-level 0 \
  --log-requests-format json \
  --log-requests-target ./artifacts/sglang-logs \
  --export-metrics-to-file \
  --export-metrics-to-file-dir ./artifacts/request-metrics
```

Do not enable every tracing and debugging option at once. Use separate modes:

- baseline mode;
- application profiling mode;
- server tracing mode;
- source instrumentation mode.

### Phase 2: Minimal LangGraph Implementation of the KVFlow Workflow

Implement:

```text
START
  Planner
  Executor
  Expresser
  Reviewer
  Planner or END
```

The graph state should carry:

- `thread_id`;
- `workflow_run_id`;
- `benchmark_run_id`;
- `turn_id`;
- `previous_agent_id`;
- `messages`;
- planner state;
- executor result;
- expresser output;
- reviewer feedback.

All agent nodes must call one shared profiled SGLang client. Do not duplicate request logic inside individual nodes.

### Phase 3: MLflow Tracing

Initialize MLflow before invoking the graph:

```python
import mlflow

mlflow.set_tracking_uri("http://localhost:5000")
mlflow.set_experiment("agent-specific-kv-cache-profiling")
mlflow.langchain.autolog(log_traces=True, run_tracer_inline=True)
```

Use the LangGraph `thread_id` for persistent workflow grouping.

### Phase 4: Instrumented SGLang Client

Every model request must go through a shared client wrapper that:

1. creates `request_uuid`;
2. attaches correlation metadata;
3. starts an MLflow child span;
4. records submit time;
5. records first-token time when streaming is enabled;
6. collects final usage;
7. reads `cached_tokens`;
8. calculates derived metrics;
9. writes span attributes;
10. appends one canonical request record.

The first implementation may be non-streaming, but TTFT and TPOT require streaming and should be added next.

### Phase 5: Integrate Client into LangGraph Nodes

Each agent node should pass:

- `workflow_id`;
- `workflow_run_id`;
- `benchmark_run_id`;
- `agent_id`;
- `previous_agent_id`;
- `turn_id`;
- `messages`;
- model parameters.

All returned measurements should use the canonical schema.

### Phase 6: Server-State Sampling

Sample SGLang metrics throughout each experiment. Write raw samples to an artifact instead of logging every high-frequency sample as a top-level MLflow metric.

Recommended intervals:

- 250 ms for short controlled experiments;
- 1 s for longer experiments.

### Phase 7: Prompt Instrumentation

Record raw prompts, serialized prompts, token IDs, hashes, template versions, and prompt layout components. Use this data to determine the first token index where two agent prompts diverge.

### Phase 8: Source-Level SGLang Instrumentation

Add cache lifecycle events only after the request-level profiler has been validated. Propagate `request_uuid`, `workflow_id`, `agent_id`, `turn_id`, `mlflow_trace_id`, and `mlflow_span_id` into SGLang before emitting backend events.

## Validation Tests

The profiler must pass these tests before larger experiments.

### Cold Request

Restart SGLang and send one request.

Expected:

```text
cached_tokens is approximately 0
```

### Exact Repeated Request

Send the identical request twice.

Expected:

```text
second.cached_tokens > first.cached_tokens
second.new_prefill_tokens < first.new_prefill_tokens
second.ttft_ms < first.ttft_ms
```

### Appended Conversation

Send a second request whose prompt contains the first request as an exact
prefix plus additional messages.

Expected:

```text
cached_tokens is approximately the reusable earlier prefix length
```

### One-Token Divergence

Construct two prompts that differ near the beginning.

Expected:

```text
cached prefix ends near the first token difference
```

### Identifier Completeness

Every model invocation must have:

```text
workflow_id
workflow_run_id
agent_id
turn_id
request_uuid
MLflow span
canonical request record
```

Target:

```text
request_to_span_join_rate = 100%
```

### Cache-Report Sanity

For every request:

```text
0 <= cached_tokens <= prompt_tokens
```

```text
new_prefill_tokens = max(prompt_tokens - cached_tokens, 0)
```

### Timing Consistency

For every request:

```text
ttft_ms <= e2e_ms
```

For streaming requests:

```text
submit_time <= first_token_time <= last_token_time <= complete_time
```

### Instrumentation Overhead

Compare the same workload under:

- profiling disabled;
- MLflow tracing only;
- MLflow plus metrics scraper;
- full server tracing;
- source-level cache instrumentation.

Report measured overhead. Do not assume it is negligible.

## Initial Experimental Matrix

Run controlled experiments before changing cache policies.

### Prefix Caching Enabled vs Disabled

Compare:

```text
radix cache enabled
radix cache disabled
```

Measure workflow completion time, per-agent TTFT, new prefill tokens, token throughput, and cache-hit ratio.

### Cold vs Warm Workflows

Compare cold-cache execution with repeated warm-cache execution.

Measure cache warm-up time, steady-state hit ratio, and which agents benefit after repeated execution.

### Self-Agent Reuse

Invoke the same agent repeatedly while extending its own history:

```text
Planner turn 1
Planner turn 2
Planner turn 3
```

### Cross-Agent Shared Prefix

Construct controlled prompts:

```text
shared prefix + planner suffix
shared prefix + reviewer suffix
```

Measure whether the second agent reuses the prefix created by the first.

### Prompt-Layout Sensitivity

Compare:

```text
agent role + shared document
```

against:

```text
shared document + agent role
```

### Workflow Topology

Use the KVFlow loop as the main topology:

```text
Planner -> Executor -> Expresser -> Reviewer -> Planner
```

Additional topologies may be introduced only as explicit experiments.

### Cache Pressure

Increase:

- prompt length;
- number of active workflows;
- workflow concurrency;
- number of distinct workflows;
- dynamic suffix length.

Identify the transition from:

```text
capacity sufficient
partial eviction
heavy cache thrashing
```

### Inter-Workflow Interference

Run Workflow A alone, then run Workflow A concurrently with unrelated Workflow
B workloads.

Measure:

```text
interference_penalty =
    latency_for_A_when_concurrent
    /
    latency_for_A_when_isolated
```

### Eviction-Policy Comparison

When supported by the SGLang version under test, compare cache policies such as LRU, LFU, SLRU, and priority-based variants.

Measure global hit rate, per-agent hit rate, recompute burden, p50 and p95 TTFT, workflow completion time, and fairness among workflows.

## Analysis Requirements

Produce:

- per-agent summaries;
- agent-transition matrices;
- cache-hit ratio versus TTFT plots;
- prompt tokens versus new prefill tokens plots;
- cache pressure curves;
- workflow critical-path summaries.

Important transition matrix dimensions:

```text
previous_agent_id -> current_agent_id
```

Example:

```text
Planner -> Executor
Executor -> Expresser
Expresser -> Reviewer
Reviewer -> Planner
```

## Source-Level Provenance Metrics

When cache provenance events are available, calculate:

```text
self_reuse_ratio =
    tokens_reused_from_same_agent
    /
    all_cached_tokens
```

```text
cross_agent_reuse_ratio =
    tokens_reused_from_other_agents
    /
    all_cached_tokens
```

```text
cross_workflow_reuse_ratio =
    tokens_reused_from_other_workflows
    /
    all_cached_tokens
```

These metrics are not reliable from `cached_tokens` alone. They require controlled request ordering or source-level cache-node metadata.

## Reproducibility Requirements

Every MLflow run should log:

- source-code commit;
- dependency lock file;
- SGLang launch command;
- model revision;
- tokenizer revision;
- chat template;
- prompt template version;
- workflow graph definition;
- workload dataset or generation seed;
- hardware information;
- server logs;
- raw request records;
- sampled server metrics;
- generated plots and analysis outputs.

Preserve raw measurements. Do not keep only aggregated charts.

## Coding Rules for Future Agents

- Use the KVFlow workflow names: `planner`, `executor`, `expresser`, `reviewer`.
- Do not silently rename `expresser` to `verifier`, `responder`, or `summarizer`.
- Keep one shared SGLang client wrapper for all agent nodes.
- Keep one canonical request schema.
- Generate request IDs before sending requests to SGLang.
- Store raw prompts and serialized prompts as project artifacts.
- Keep deterministic benchmark settings unless an experiment explicitly varies them.
- Separate request-level measurements, server-level observations, and inferred values.
- Do not attribute global cache changes to one request under concurrency unless source-level events prove it.
- Add source-level instrumentation only after the basic profiler passes validation.
- Prefer reproducible configuration files over hard-coded experiment settings.
- Do not optimize cache policies before baseline characterization is complete.

## Minimum Viable Profiler

The MVP is complete when it can:

1. display the KVFlow workflow as an MLflow trace;
2. identify every agent and model invocation;
3. report prompt tokens and cached tokens for every request;
4. calculate newly computed prompt tokens and cache-hit ratio;
5. measure TTFT and end-to-end latency;
6. group traces by workflow thread;
7. export one canonical request table;
8. compare cold-cache and warm-cache experiments;
9. generate per-agent and transition-level summaries;
10. reproduce results from saved configuration.

Eviction provenance, cache-node residency, CPU-GPU cache movement, and RL-driven policy decisions are not required for the MVP.

## References

- KVFlow paper: https://arxiv.org/abs/2507.07400
- KVFlow repository: https://github.com/PanZaifeng/KVFlow
- PEER workflow paper: https://arxiv.org/abs/2407.06985
- SGLang documentation: https://docs.sglang.ai/
- MLflow documentation: https://mlflow.org/docs/latest/
- Agent-Specific KV-Cache Profiler with LangGraph, SGLang, and MLflow documentation: https://yanboyang.com/posts/2026-06-24-143948-building_an_agent_specific_kv_cache_profiler_with_langgraph_sglang_and_mlflow
