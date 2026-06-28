# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Martino Pilia

import os

from dazelisk.utils import (
    HostUser,
    _run_subprocess,
    get_host_user,
    worktree_lock,
)


def test_run_subprocess_returns_captured_output():
    result = _run_subprocess(["printf", "hello"], capture_output=True)
    assert result.stdout == "hello"
    assert result.returncode == 0


def test_run_subprocess_returns_exit_code_without_raising_when_unchecked():
    result = _run_subprocess(["false"], check=False)
    assert result.returncode != 0


def test_get_host_user_matches_current_process():
    user = get_host_user()
    assert isinstance(user, HostUser)
    assert user.uid == os.getuid()
    assert user.gid == os.getgid()
    assert user.home


def test_get_host_user_honours_home_env(monkeypatch):
    monkeypatch.setenv("HOME", "/home/forwarded")
    assert get_host_user().home == "/home/forwarded"


def test_worktree_lock_is_reentrant_round_trip(tmp_path):
    lock = tmp_path / "lock"
    with worktree_lock(lock):
        pass
    # Re-acquiring after release must succeed.
    with worktree_lock(lock):
        pass
