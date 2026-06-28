# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Martino Pilia

"""Generation of minimal passwd/group files mounted into the container."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from dazelisk.naming import TEMP_DIR
from dazelisk.utils import HostUser

logger = logging.getLogger(__name__)

PASSWD_PREFIX = "dazelisk-passwd-"
GROUP_PREFIX = "dazelisk-group-"

_SHELL = "/bin/bash"


def generate_passwd(user: HostUser) -> str:
    """Minimal passwd with root and the host user (home set to host $HOME)."""
    return (
        f"root:x:0:0:root:/root:{_SHELL}\n"
        f"{user.username}:x:{user.uid}:{user.gid}:{user.username}:{user.home}:{_SHELL}\n"
    )


def generate_group(user: HostUser) -> str:
    """Minimal group with root and the host user's primary group."""
    return f"root:x:0:\n{user.groupname}:x:{user.gid}:\n"


def passwd_path(uid: int, worktree_sha: str, temp_dir: Path = TEMP_DIR) -> Path:
    return temp_dir / f"{PASSWD_PREFIX}{uid}-{worktree_sha}"


def group_path(uid: int, worktree_sha: str, temp_dir: Path = TEMP_DIR) -> Path:
    return temp_dir / f"{GROUP_PREFIX}{uid}-{worktree_sha}"


def _write_secure(path: Path, content: str) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as handle:
        handle.write(content)
    path.chmod(0o600)  # enforce 0600 even when overwriting an existing file


def write_passwd_group(
    user: HostUser, worktree_sha: str, temp_dir: Path = TEMP_DIR
) -> tuple[Path, Path]:
    """Write passwd/group files (0600, overwriting if present) and return paths.

    The files are not cleaned up: they hold no secrets, must outlive a single
    invocation (the container is reused across runs), and are reaped with /tmp.
    """
    passwd = passwd_path(user.uid, worktree_sha, temp_dir)
    group = group_path(user.uid, worktree_sha, temp_dir)
    _write_secure(passwd, generate_passwd(user))
    _write_secure(group, generate_group(user))
    return passwd, group
