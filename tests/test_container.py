# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Martino Pilia

import pytest

from dazelisk import container, docker, gpu, user_mapping, volume
from dazelisk.container import ensure_container, run_in_container
from dazelisk.naming import ResourceNames
from dazelisk.utils import HostUser

USER = HostUser(uid=1000, gid=1000, username="alice", groupname="devs", home="/home/alice")


@pytest.fixture
def names(tmp_path):
    return ResourceNames(
        image="img:1",
        uid=1000,
        worktree_sha="abc123",
        container="dazelisk-x-1000-abc123",
        volume="dazelisk-cache-1000",
        lock_path=tmp_path / "lock",
    )


@pytest.fixture
def fake_docker(monkeypatch):
    """Cut the Docker dependency; record lifecycle operations."""
    calls = {"created": [], "removed": []}
    state = {"exists": False, "running": False, "image": True, "volume": True}

    monkeypatch.setattr(docker, "image_exists", lambda image: state["image"])
    monkeypatch.setattr(docker, "pull_image", lambda image: calls.setdefault("pulled", image))
    monkeypatch.setattr(volume, "volume_exists", lambda name: state["volume"])
    monkeypatch.setattr(volume, "create_volume", lambda name: calls.setdefault("volume_created", name))
    monkeypatch.setattr(volume, "ensure_volume_permissions", lambda *a, **k: calls.setdefault("perms", a))
    monkeypatch.setattr(docker, "container_is_running", lambda name: state["running"])
    monkeypatch.setattr(docker, "remove_container", lambda name: calls["removed"].append(name))
    monkeypatch.setattr(docker, "create_container", lambda spec: calls["created"].append(spec))
    monkeypatch.setattr(user_mapping, "write_passwd_group", lambda user, sha: ("/tmp/p", "/tmp/g"))
    monkeypatch.setattr(gpu, "should_enable_gpus", lambda env: False)
    return calls, state


def test_running_container_is_reused(fake_docker, names):
    calls, state = fake_docker
    state.update(exists=True, running=True)
    ensure_container(names, USER, env={})
    assert calls["created"] == []
    assert calls["removed"] == []


def test_stopped_container_is_removed_and_recreated(fake_docker, names):
    calls, state = fake_docker
    state.update(running=False)
    ensure_container(names, USER, env={})
    assert names.container in calls["removed"]
    assert len(calls["created"]) == 1


def test_created_container_carries_uid_label_and_entrypoint(fake_docker, names):
    calls, _ = fake_docker
    ensure_container(names, USER, env={})
    spec = calls["created"][0]
    assert spec.labels == {"dazelisk.uid": "1000"}
    assert spec.entrypoint == container.CONTAINER_ENTRYPOINT
    assert spec.user == "1000:1000"
    assert spec.home == "/home/alice"


def test_missing_image_is_pulled(fake_docker, names):
    calls, state = fake_docker
    state["image"] = False
    ensure_container(names, USER, env={})
    assert calls["pulled"] == "img:1"


def test_volume_created_and_permissioned_when_absent(fake_docker, names):
    calls, state = fake_docker
    state["volume"] = False
    ensure_container(names, USER, env={})
    assert calls["volume_created"] == "dazelisk-cache-1000"
    assert "perms" in calls


def test_existing_volume_is_not_repermissioned(fake_docker, names):
    calls, state = fake_docker
    state["volume"] = True
    ensure_container(names, USER, env={})
    assert "perms" not in calls


def test_run_in_container_forwards_exit_code(monkeypatch):
    monkeypatch.setattr(docker, "exec_container", lambda *a, **k: 42)
    assert run_in_container("c", ["bazelisk", "build"], tty=False) == 42


def test_run_in_container_forces_tty_when_requested(monkeypatch):
    captured = {}
    monkeypatch.setattr(docker, "exec_container", lambda name, cmd, **k: captured.update(k) or 0)
    run_in_container("c", ["bash"], as_root=True, tty=True)
    assert captured["tty"] is True
    assert captured["as_root"] is True
