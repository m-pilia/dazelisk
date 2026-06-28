# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Martino Pilia

"""Docker volume management for the per-user cache."""

from __future__ import annotations

import logging

from dazelisk.docker import DOCKER_CLI
from dazelisk.utils import _run_subprocess

logger = logging.getLogger(__name__)

# Mount point of the cache volume inside the throwaway permission-fix container.
_PERMISSION_FIX_TARGET = "/cache"


def volume_exists(name: str) -> bool:
    result = _run_subprocess(
        [DOCKER_CLI, "volume", "inspect", name],
        check=False,
        capture_output=True,
    )
    return result.returncode == 0


def create_volume(name: str) -> None:
    logger.info("creating cache volume %s", name)
    _run_subprocess([DOCKER_CLI, "volume", "create", name], capture_output=True)


def _permission_fix_args(
    volume_name: str, uid: int, gid: int, image: str
) -> list[str]:
    return [
        DOCKER_CLI, "run", "--rm",
        "--user", "0:0",
        "--entrypoint", "chown",
        "--volume", f"{volume_name}:{_PERMISSION_FIX_TARGET}",
        image, f"{uid}:{gid}", _PERMISSION_FIX_TARGET,
    ]


def ensure_volume_permissions(
    volume_name: str, uid: int, gid: int, image: str
) -> None:
    """Give the host user ownership of the cache volume root.

    Run once, right after volume creation: a fresh volume is owned by root, so
    the unprivileged container user could not otherwise write its cache.
    """
    logger.info("setting ownership of volume %s to %s:%s", volume_name, uid, gid)
    _run_subprocess(
        _permission_fix_args(volume_name, uid, gid, image),
        capture_output=True,
    )


def get_volume_mountpoint(volume_name: str) -> str:
    result = _run_subprocess(
        [DOCKER_CLI, "volume", "inspect", "--format", "{{.Mountpoint}}", volume_name],
        capture_output=True,
    )
    return result.stdout.strip()
