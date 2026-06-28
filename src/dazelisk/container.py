# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Martino Pilia

"""Container lifecycle: ensure image/volume/container, then exec commands."""

from __future__ import annotations

import logging
import os
import sys
from collections.abc import Mapping
from pathlib import Path

from dazelisk import customization, docker, gpu, naming, user_mapping, volume
from dazelisk.naming import ResourceNames
from dazelisk.utils import HostUser, worktree_lock

logger = logging.getLogger(__name__)

CONTAINER_ENTRYPOINT = ["sleep", "infinity"]


def _ensure_image(image: str) -> None:
    if not docker.image_exists(image):
        docker.pull_image(image)


def _ensure_volume(names: ResourceNames, user: HostUser) -> None:
    if not volume.volume_exists(names.volume):
        volume.create_volume(names.volume)
        volume.ensure_volume_permissions(names.volume, user.uid, user.gid, names.image)


def ensure_container(
    names: ResourceNames,
    user: HostUser,
    env: Mapping[str, str] | None = None,
) -> None:
    """Ensure image, cache volume, and a running container all exist.

    Reuses a running container; removes and recreates a stopped one; creates a
    fresh one when absent. The image/volume/container critical section is
    serialised by a per-worktree lock; concurrent ``docker exec`` is unaffected.
    """
    env = os.environ if env is None else env
    with worktree_lock(names.lock_path):
        _ensure_image(names.image)
        _ensure_volume(names, user)
        if docker.container_is_running(names.container):
            logger.debug("reusing running container %s", names.container)
            return
        docker.remove_container(names.container)
        passwd, group = user_mapping.write_passwd_group(user, names.worktree_sha)
        docker.create_container(
            docker.ContainerSpec(
                name=names.container,
                image=names.image,
                user=f"{user.uid}:{user.gid}",
                home=user.home,
                worktree=str(names.worktree_root),
                cache_volume=names.volume,
                passwd_path=str(passwd),
                group_path=str(group),
                labels={naming.UID_LABEL_KEY: str(user.uid)},
                extra_mounts=customization.parse_mounts(env.get("DAZELISK_MOUNTS")),
                env_args=customization.parse_environment(env.get("DAZELISK_ENVIRONMENT"), env),
                ports=customization.parse_ports(env.get("DAZELISK_PORTS")),
                gpus=gpu.should_enable_gpus(env),
                entrypoint=CONTAINER_ENTRYPOINT,
            )
        )


def run_in_container(
    name: str,
    command: list[str],
    *,
    as_root: bool = False,
    tty: bool | None = None,
    workdir: str | None = None,
) -> int:
    """Exec a command, returning its exit code.

    Runs in the host's current working directory (mirrored into the container via
    the identical-path worktree mount). TTY is auto-detected unless forced.
    """
    if tty is None:
        tty = sys.stdin.isatty() and sys.stdout.isatty()
    if workdir is None:
        workdir = str(Path.cwd())
    return docker.exec_container(
        name, command, as_root=as_root, interactive=True, tty=tty, workdir=workdir
    )
