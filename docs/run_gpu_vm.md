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

If `docker` is not installed, follow
[docs/install_docker_gpu_ubuntu.md](install_docker_gpu_ubuntu.md) first.

## Configure

`MODEL_PATH` is required. The other values below already have Compose defaults,
but exporting them makes the run explicit and repeatable.

Default configuration for the RTX 2070 test VM:

```bash
export MODEL_PATH="Qwen/Qwen2.5-0.5B-Instruct"
export SERVED_MODEL_NAME="profiler-model"
export PROMPT="Profile how this workflow reuses KV cache."
export SGLANG_IMAGE="lmsysorg/sglang:latest"
```

`MODEL_PATH` can be a Hugging Face model id or a container-visible local model
path. Choose a model that fits the GPU memory.

Examples:

```bash
# Small public Hugging Face model for the default RTX 2070 path.
export MODEL_PATH="Qwen/Qwen2.5-0.5B-Instruct"

# Local model directory mounted or available inside the SGLang container.
export MODEL_PATH="/models/Qwen2.5-0.5B-Instruct"
```

If `MODEL_PATH` is not set, Docker Compose stops before launching SGLang with an
error like:

```text
variable MODEL_PATH is required: Set MODEL_PATH to a Hugging Face model id or a container-visible model path
```

For gated Hugging Face models:

```bash
export HF_TOKEN="<your-token>"
```

Runtime defaults used by `compose.gpu.yaml`:

```text
SERVED_MODEL_NAME=profiler-model
PROMPT=Profile how this workflow reuses KV cache.
SGLANG_IMAGE=lmsysorg/sglang:latest
profiler --sglang-url=http://sglang:30000
profiler --mlflow-tracking-uri=http://mlflow:5000
profiler --requests-jsonl=artifacts/requests.jsonl
profiler --prompt-artifact-dir=artifacts/prompts
profiler --max-turns=1
```

## Start MLflow And SGLang

The SGLang image is large. Check free disk space before the first pull:

```bash
df -h /
docker system df
```

Keep at least 80 GB free for Docker images, temporary pull layers, model cache,
and run artifacts. The compressed SGLang image is roughly 13 GB, but Docker can
need substantially more space while extracting layers. If extraction fails and
then `df -h /` looks normal again, containerd likely cleaned up the failed
temporary snapshot after running out of space.

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
