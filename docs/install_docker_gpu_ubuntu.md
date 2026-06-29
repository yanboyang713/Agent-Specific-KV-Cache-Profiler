# Install Docker GPU Support On Ubuntu

Use this when the GPU VM has NVIDIA drivers but `docker` is missing:

```text
Command 'docker' not found
```

The project runbook expects Docker Engine, Docker Compose, and NVIDIA Container
Toolkit to be available before starting SGLang.

## 1. Verify The NVIDIA Driver

```bash
nvidia-smi
```

If this fails, fix the host GPU driver or VM GPU passthrough first. Docker cannot
make an unavailable GPU visible.

## 2. Install Docker Engine

Prefer the Docker apt repository over the Snap package for GPU workloads.

```bash
sudo apt update
sudo apt install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

Start Docker:

```bash
sudo systemctl enable --now docker
docker compose version
```

If `docker compose version` works only with `sudo`, continue with the next
section.

## 3. Allow Non-Root Docker Commands

```bash
sudo usermod -aG docker "$USER"
newgrp docker
```

Verify:

```bash
docker run --rm hello-world
```

If the group change does not apply in the current SSH session, log out and log
back in.

## 4. Install NVIDIA Container Toolkit

```bash
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
  sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt update
sudo apt install -y nvidia-container-toolkit
```

Configure Docker to use the NVIDIA runtime:

```bash
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

## 5. Verify GPU Access In Docker

```bash
docker run --rm --gpus all ubuntu nvidia-smi
```

This must show the same GPU as the host `nvidia-smi`. After this passes, return
to the main runbook:

```text
docs/run_gpu_vm.md
```

## Common Failures

`docker: command not found`

Docker Engine is not installed or not on `PATH`. Complete step 2.

`permission denied while trying to connect to the Docker daemon socket`

Your user is not in the `docker` group, or the current shell has not picked up
the group change. Complete step 3 and reconnect over SSH if needed.

`could not select device driver "" with capabilities: [[gpu]]`

Docker is installed, but NVIDIA Container Toolkit is missing or Docker was not
restarted after configuration. Complete step 4.

`nvidia-smi` works on the host but fails inside Docker

Re-run:

```bash
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
docker run --rm --gpus all ubuntu nvidia-smi
```

`no space left on device` while pulling `lmsysorg/sglang`

Docker ran out of disk space under `/var/lib/docker` or `/var/lib/containerd`.
The SGLang image is large, and Docker needs extra temporary space while pulling
and unpacking layers. Keep at least 80 GB free before pulling SGLang. If
extraction fails and then `df -h /` looks normal again, containerd likely cleaned
up the failed temporary snapshot after running out of space.

Check usage:

```bash
df -h /
sudo du -sh /var/lib/docker /var/lib/containerd 2>/dev/null || true
docker system df
```

If there are no important local containers or images, clean unused Docker data:

```bash
docker system prune -af
docker builder prune -af
```

Then retry:

```bash
docker compose -f compose.gpu.yaml pull sglang
docker compose -f compose.gpu.yaml up mlflow sglang
```

If the root filesystem has less than 80 GB free, expand the VM disk or move
Docker's data root to a larger mounted disk before retrying.

On Ubuntu Server installs that use the default LVM layout, check whether the
volume group already has unused space:

```bash
lsblk
sudo vgs
sudo lvs
```

If `sudo vgs` shows free space in the volume group, expand the root logical
volume and filesystem:

```bash
sudo lvextend -r -l +100%FREE /dev/mapper/ubuntu--vg-ubuntu--lv
df -h /
```

If the VM disk was expanded but the volume group still has no free space, grow
the partition and physical volume first. Confirm the disk and partition names
with `lsblk`; the common Ubuntu layout is disk `/dev/sda` with LVM partition
`/dev/sda3`:

```bash
sudo growpart /dev/sda 3
sudo pvresize /dev/sda3
sudo lvextend -r -l +100%FREE /dev/mapper/ubuntu--vg-ubuntu--lv
df -h /
```
