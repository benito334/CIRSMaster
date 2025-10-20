# GPU Setup

- Install NVIDIA drivers and verify `nvidia-smi`.
- Install NVIDIA Container Toolkit (see NVIDIA docs).
- Test container GPU access with:

```bash
docker run --rm --gpus all nvidia/cuda:12.2.2-base-ubuntu22.04 nvidia-smi
```

- Ensure Compose services using GPU have device reservations configured.
