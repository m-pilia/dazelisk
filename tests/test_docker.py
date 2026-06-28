# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Martino Pilia

from dataclasses import replace

from dazelisk.docker import (
    ContainerSpec,
    _build_exec_args,
    _build_run_args,
)

SPEC = ContainerSpec(
    name="dazelisk-abc-1000-def",
    image="docker.io/library/dazelisk:1.0.0-1",
    user="1000:1000",
    home="/home/u",
    worktree="/home/u/repo",
    cache_volume="dazelisk-cache-1000",
    passwd_path="/tmp/dazelisk-passwd-1000-def",
    group_path="/tmp/dazelisk-group-1000-def",
    labels={"dazelisk.uid": "1000"},
    entrypoint=["sleep", "infinity"],
)


def _values(args, flag):
    """Values of repeated ``--flag=value`` arguments."""
    prefix = f"{flag}="
    return [a.removeprefix(prefix) for a in args if a.startswith(prefix)]


def test_run_args_use_detached_named_container():
    args = _build_run_args(SPEC)
    assert args[:2] == ["docker", "run"]
    assert "--detach" in args
    assert _values(args, "--name") == ["dazelisk-abc-1000-def"]


def test_run_args_apply_label_user_and_home():
    args = _build_run_args(SPEC)
    assert "dazelisk.uid=1000" in _values(args, "--label")
    assert _values(args, "--user") == ["1000:1000"]
    assert "HOME=/home/u" in _values(args, "--env")


def test_run_args_mount_cache_passwd_and_group():
    volumes = _values(_build_run_args(SPEC), "--volume")
    assert "dazelisk-cache-1000:/home/u/.cache" in volumes
    assert "/tmp/dazelisk-passwd-1000-def:/etc/passwd:ro" in volumes
    assert "/tmp/dazelisk-group-1000-def:/etc/group:ro" in volumes


def test_run_args_mount_worktree_at_identical_path():
    volumes = _values(_build_run_args(SPEC), "--volume")
    assert "/home/u/repo:/home/u/repo" in volumes


def test_run_args_image_is_last_before_entrypoint():
    args = _build_run_args(SPEC)
    idx = args.index(SPEC.image)
    assert args[idx + 1 :] == ["sleep", "infinity"]


def test_run_args_include_custom_mounts_env_ports_and_gpu():
    spec = replace(
        SPEC,
        extra_mounts=["type=bind,src=/data,dst=/data,ro"],
        env_args=["MY_SECRET", "MY_TOGGLE=on"],
        ports=["8080:80"],
        gpus=True,
    )
    args = _build_run_args(spec)
    assert _values(args, "--mount") == ["type=bind,src=/data,dst=/data,ro"]
    assert "MY_SECRET" in _values(args, "--env")
    assert "MY_TOGGLE=on" in _values(args, "--env")
    assert _values(args, "--publish") == ["8080:80"]
    assert "--gpus=all" in args


def test_run_args_omit_gpu_by_default():
    assert "--gpus=all" not in _build_run_args(SPEC)


def test_exec_args_default_interactive_no_tty():
    args = _build_exec_args(
        "c", ["bazelisk", "build"], as_root=False, interactive=True, tty=False, workdir=None
    )
    assert args[:2] == ["docker", "exec"]
    assert "--interactive" in args
    assert "--tty" not in args
    assert "--user=0:0" not in args
    assert not any(a.startswith("--workdir=") for a in args)
    assert args[-3:] == ["c", "bazelisk", "build"]


def test_exec_args_root_tty_and_workdir():
    args = _build_exec_args(
        "c", ["bash"], as_root=True, interactive=True, tty=True, workdir="/home/u/repo"
    )
    assert "--user=0:0" in args
    assert "--tty" in args
    assert "--workdir=/home/u/repo" in args
