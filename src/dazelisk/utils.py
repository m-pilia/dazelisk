# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Martino Pilia

"""Host introspection and the single subprocess entry point."""

from __future__ import annotations

import fcntl
import grp
import logging
import os
import pwd
import shlex
import subprocess
import time
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


def _run_subprocess(
    args: Sequence[str],
    *,
    check: bool = True,
    capture_output: bool = False,
    text: bool = True,
) -> subprocess.CompletedProcess:
    """Run a subprocess, timing it and logging the command at DEBUG.

    This is the only place in the codebase that invokes ``subprocess``. Args are
    always passed as a list (never ``shell=True``) so values are never subject to
    shell interpretation.
    """
    logger.debug("exec: %s", shlex.join(args))
    start = time.perf_counter()
    try:
        return subprocess.run(
            list(args),
            check=check,
            capture_output=capture_output,
            text=text,
        )
    finally:
        elapsed = time.perf_counter() - start
        logger.debug("exec done in %.3fs: %s", elapsed, args[0] if args else "")


@dataclass(frozen=True)
class HostUser:
    uid: int
    gid: int
    username: str
    groupname: str
    home: str


def get_host_user() -> HostUser:
    """Current user's identity, using the primary group only."""
    pw = pwd.getpwuid(os.getuid())
    return HostUser(
        uid=pw.pw_uid,
        gid=os.getgid(),
        username=pw.pw_name,
        groupname=grp.getgrgid(os.getgid()).gr_name,
        home=os.environ.get("HOME") or pw.pw_dir,
    )


@contextmanager
def worktree_lock(lock_path: Path) -> Iterator[None]:
    """Exclusive advisory lock serialising the container ensure/create section."""
    with lock_path.open("w") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)
