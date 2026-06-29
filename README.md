# Agent-Specific KV-Cache Profiler

Initial implementation of the baseline KVFlow-style profiler described in
`agents.md`. The profiler is intended to support other LangGraph multi-agent
workflow variants in future experiments.

The first slice focuses on request-level profiling:

- baseline agent identities: `planner`, `executor`, `expresser`, `reviewer`;
- one shared OpenAI-compatible SGLang client wrapper;
- generated `request_uuid` values before model calls;
- canonical JSONL records with cache and latency fields;
- optional Parquet export when `pandas` and `pyarrow` are installed;
- required LangGraph workflow execution with MLflow Tracing.

Use Docker/OCI containers for reproducible project runs. The profiler client does not need direct GPU access, but the SGLang serving container usually does.

For a complete single-GPU-VM runbook using Docker Compose, see
[docs/run_gpu_vm.md](docs/run_gpu_vm.md).

## Repository Structure

The repository follows the Phase 0 structure from the Org-roam note, adapted to a
standard installable Python `src/` layout:

```text
Agent-Specific-KV-Cache-Profiler/
  configs/
    sglang.yaml
    workflow.yaml
    experiments/
  src/kv_cache_profiler/
    schema.py
    mlflow_integration.py
    client.py
    environment.py
    workflow.py
    analysis.py
  workflows/
    synthetic/
    kubernetes_aiops/
  sglang_instrumentation/
  experiments/
  analysis/
  tests/
  artifacts/
```

The Org note's `profiler/` directory maps to `src/kv_cache_profiler/` here so
the package remains installable with `pip install -e`. Generated run outputs
belong under `artifacts/`; only `artifacts/.gitkeep` is tracked.

## Docker-First Runtime

This project is intended to run on one GPU VM with one NVIDIA GeForce RTX 2070.
Connect to the VM with:

```bash
ssh -p 2222 yanboyang713@wifione.yanboyang.com
```

Recommended single-VM container split:

- SGLang: run in one GPU-enabled container using the RTX 2070.
- Profiler: run as a CPU container that calls the SGLang OpenAI-compatible API.
- MLflow: run as a container and persist its tracking data on a bind-mounted
  volume.
- Artifacts: bind mount `artifacts/` so request records, prompt artifacts, logs,
  and analysis outputs survive container removal.

After SSHing into the GPU VM, verify that Docker can see the RTX 2070:

```bash
nvidia-smi
docker run --rm --gpus all ubuntu nvidia-smi
```

Then use the compose runbook:

```bash
export MODEL_PATH="Qwen/Qwen2.5-0.5B-Instruct"
export SERVED_MODEL_NAME="profiler-model"
mkdir -p artifacts/mlflow artifacts/sglang/request_metrics artifacts/sglang/request_logs artifacts/prompts
docker compose -f compose.gpu.yaml build mlflow profiler
docker compose -f compose.gpu.yaml up mlflow sglang
```

In a second SSH session, run the profiler:

```bash
export MODEL_PATH="Qwen/Qwen2.5-0.5B-Instruct"
export PROMPT="Profile how this workflow reuses KV cache."
docker compose -f compose.gpu.yaml --profile run run --rm profiler
```

The MLflow UI is exposed on port `5000`, and SGLang is exposed on port `30000`.
Use SSH port forwarding if those ports are not directly reachable from your
local machine.

## GPU Support in Docker

Yes. Docker supports NVIDIA GPU access on Linux when the host has:

- a working NVIDIA driver;
- the NVIDIA Container Toolkit installed and configured for Docker;
- a GPU visible to the host, VM, or LXC before Docker starts the container.

Verify the host first:

```bash
nvidia-smi
```

Then verify Docker GPU access:

```bash
docker run --rm --gpus all ubuntu nvidia-smi
```

For Docker Compose, reserve GPUs on the SGLang service, not the profiler service:

```yaml
services:
  sglang:
    image: <pin-sglang-cuda-image>
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

Docker does not make a hidden Proxmox GPU available by itself. GPU passthrough or
device mapping must work first, and `nvidia-smi` should succeed in the host,
VM, or LXC where Docker Engine runs.

## MLflow Tracing for LangGraph

LangGraph and MLflow are required dependencies for this project. Use MLflow
Tracing for every LangGraph workflow run; do not treat tracing as an optional
debug mode.

Start MLflow before running the profiler:

```bash
docker build -f Dockerfile.mlflow -t kv-cache-profiler-mlflow .
mkdir -p artifacts/mlflow
docker run --rm \
  --name kv-cache-profiler-mlflow \
  -p 5000:5000 \
  -v "$PWD/artifacts/mlflow:/mlflow" \
  kv-cache-profiler-mlflow
```

MLflow needs to be reachable before the profiler starts because the profiler
initializes tracing before invoking the LangGraph workflow. It sets the tracking
URI, selects the experiment, enables `mlflow.langchain.autolog()`, and then
executes the graph. If the tracking server is unavailable, the run cannot
reliably persist LangGraph traces, SGLang request spans, session metadata, or
artifacts to the shared MLflow UI.

The profiler initializes MLflow with LangChain autologging because MLflow traces
LangGraph through its LangChain integration:

```python
import mlflow

mlflow.set_tracking_uri("http://localhost:5000")
mlflow.set_experiment("agent-specific-kv-cache-profiling")
mlflow.langchain.autolog()
```

LangGraph invocations must include the workflow `thread_id` in the runnable
config so MLflow can group traces into sessions:

```python
graph.invoke(state, config={"configurable": {"thread_id": state["thread_id"]}})
```

## Quick Start

Run a single baseline KVFlow pass against an SGLang server:

```bash
python -m kv_cache_profiler.cli run \
  --prompt "Profile how this workflow reuses KV cache." \
  --sglang-url http://localhost:30000 \
  --model profiler-model \
  --mlflow-tracking-uri http://localhost:5000 \
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

Install the project with analysis and development extras when you need Parquet
export and the test runner:

```bash
pip install -e ".[analysis,dev]"
```
