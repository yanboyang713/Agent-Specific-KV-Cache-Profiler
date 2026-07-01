#!/usr/bin/env bash
set -euo pipefail

IMAGE="${DOCKER_GPU_TEST_IMAGE:-ubuntu:latest}"

info() {
  printf '[check-docker-gpu] %s\n' "$*"
}

fail() {
  printf '[check-docker-gpu] ERROR: %s\n' "$*" >&2
  exit 1
}

command -v nvidia-smi >/dev/null 2>&1 || fail "nvidia-smi is not available on the host."
command -v docker >/dev/null 2>&1 || fail "docker is not installed or is not in PATH."

info "Checking host GPU with nvidia-smi..."
nvidia-smi >/dev/null || fail "nvidia-smi failed on the host. Fix the NVIDIA driver or VM GPU passthrough first."

info "Checking Docker daemon..."
docker info >/dev/null || fail "docker info failed. Start Docker or fix Docker permissions for this user."

info "Checking Docker Compose plugin..."
docker compose version >/dev/null || fail "docker compose is not available."

info "Checking GPU visibility inside Docker using ${IMAGE}..."
docker run --rm --gpus all "${IMAGE}" nvidia-smi >/dev/null || fail "Docker cannot access the GPU. Install/configure NVIDIA Container Toolkit."

info "Docker GPU support is working."
