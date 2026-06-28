# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Martino Pilia

"""NVIDIA GPU passthrough detection."""

from __future__ import annotations

import logging
import os
import shutil
from collections.abc import Mapping

from dazelisk.utils import _run_subprocess

logger = logging.getLogger(__name__)

GPU_PASSTHROUGH_ENV_VAR = "DAZELISK_GPU_PASSTHROUGH"
_TRUE_VALUES = {"1", "true"}
_FALSE_VALUES = {"0", "false"}


def _passthrough_requested(value: str | None) -> bool:
    """Interpret DAZELISK_GPU_PASSTHROUGH; enabled by default, raise if invalid."""
    if value is None:
        return True
    normalised = value.strip().lower()
    if normalised in _TRUE_VALUES:
        return True
    if normalised in _FALSE_VALUES:
        return False
    raise ValueError(
        f"{GPU_PASSTHROUGH_ENV_VAR} must be one of 1/0/true/false (case-insensitive), got {value!r}"
    )


def has_nvidia_gpu() -> bool:
    if shutil.which("nvidia-smi") is None:
        return False
    result = _run_subprocess(["nvidia-smi", "-L"], check=False, capture_output=True)
    return result.returncode == 0


def has_nvidia_container_cli() -> bool:
    return shutil.which("nvidia-container-cli") is not None


def should_enable_gpus(env: Mapping[str, str] | None = None) -> bool:
    env = os.environ if env is None else env
    if not _passthrough_requested(env.get(GPU_PASSTHROUGH_ENV_VAR)):
        logger.info("GPU passthrough disabled via %s", GPU_PASSTHROUGH_ENV_VAR)
        return False
    gpu = has_nvidia_gpu()
    if gpu:
        logger.info("NVIDIA GPU detected")
    if gpu and has_nvidia_container_cli():
        logger.info("enabling GPU passthrough (--gpus all)")
        return True
    return False
