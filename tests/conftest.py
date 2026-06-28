# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Martino Pilia

import pytest


@pytest.fixture(autouse=True)
def _clear_dazelisk_env(monkeypatch):
    """Keep the host's DAZELISK_* configuration from leaking into tests."""
    for var in (
        "DAZELISK_IMAGE",
        "DAZELISK_MOUNTS",
        "DAZELISK_ENVIRONMENT",
        "DAZELISK_PORTS",
        "DAZELISK_GPU_PASSTHROUGH",
        "DAZELISK_WORKTREE_MARKERS",
    ):
        monkeypatch.delenv(var, raising=False)
