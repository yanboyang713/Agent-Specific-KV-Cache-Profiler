# Run On A GPU VM

This path runs the project on one GPU VM with Docker Compose:

- MLflow tracking server in a CPU container;
- SGLang server in a GPU container;
- profiler CLI in a CPU container.

## Prerequisites

On the GPU VM:

```bash
nvidia-smi
docker run --rm --gpus all ubuntu nvidia-smi
docker compose version
```

The second command must show the GPU from inside Docker. If it does not, fix the
NVIDIA driver or NVIDIA Container Toolkit before starting SGLang.

## Configure

Choose a model that fits the GPU memory and export it as `MODEL_PATH`.

```bash
export MODEL_PATH="Qwen/Qwen2.5-0.5B-Instruct"
export SERVED_MODEL_NAME="profiler-model"
```

For gated Hugging Face models:

```bash
export HF_TOKEN="<your-token>"
```

To override the SGLang image:

```bash
export SGLANG_IMAGE="lmsysorg/sglang:latest"
```

## Start MLflow And SGLang

```bash
mkdir -p artifacts/mlflow artifacts/sglang/request_metrics artifacts/sglang/request_logs artifacts/prompts
docker compose -f compose.gpu.yaml build mlflow profiler
docker compose -f compose.gpu.yaml up mlflow sglang
```

Wait until SGLang is healthy. The MLflow UI is available at:

```text
http://<gpu-vm-ip>:5000
```

## Run The Profiler

In a second shell on the GPU VM:

```bash
export MODEL_PATH="Qwen/Qwen2.5-0.5B-Instruct"
export PROMPT="Profile how this workflow reuses KV cache."
docker compose -f compose.gpu.yaml --profile run run --rm profiler
```

The run writes:

- request rows: `artifacts/requests.jsonl`;
- raw prompt artifacts: `artifacts/prompts/`;
- SGLang metrics/logs: `artifacts/sglang/`;
- MLflow database and artifacts: `artifacts/mlflow/`.

## Analyze Results

```bash
docker compose -f compose.gpu.yaml --profile run run --rm profiler \
  analyze \
  --requests-jsonl artifacts/requests.jsonl \
  --output-dir artifacts/analysis \
  --parquet-output artifacts/analysis/requests.parquet
```

## Stop Services

```bash
docker compose -f compose.gpu.yaml down
```
