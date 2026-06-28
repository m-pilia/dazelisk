# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Martino Pilia

import pytest

from dazelisk import cli, container, docker, workspace
from dazelisk.cli import UsageError, main, parse_args, run
from dazelisk.naming import MissingImageError

IMAGE = "my_custom/registry/dazelisk:1.0.0-1"


@pytest.fixture
def runnable(monkeypatch, tmp_path):
    """Stub out Docker and container lifecycle; record the exec call."""
    monkeypatch.setenv("DAZELISK_IMAGE", IMAGE)
    monkeypatch.setattr(docker, "check_docker_available", lambda: None)
    monkeypatch.setattr(workspace, "get_worktree_root", lambda: tmp_path)
    monkeypatch.setattr(container, "ensure_container", lambda names, user: None)
    recorded = {}

    def fake_run(name, command, *, as_root=False, tty=None):
        recorded.update(name=name, command=command, as_root=as_root, tty=tty)
        return 7

    monkeypatch.setattr(container, "run_in_container", fake_run)
    return recorded


def test_parse_args_splits_dazelisk_and_forwarded():
    args, forwarded = parse_args(["--dazelisk-as-root", "build", "//...", "--config=ci"])
    assert args.dazelisk_as_root is True
    assert forwarded == ["build", "//...", "--config=ci"]


def test_dazelisk_help_exits_zero(capsys):
    with pytest.raises(SystemExit) as exc:
        parse_args(["--dazelisk-help"])
    assert exc.value.code == 0
    assert "run bazelisk transparently" in capsys.readouterr().out


def test_image_flag_prints_and_exits_without_docker(monkeypatch, capsys):
    monkeypatch.setenv("DAZELISK_IMAGE", IMAGE)
    monkeypatch.setattr(docker, "check_docker_available", lambda: pytest.fail("no docker"))
    assert main(["--dazelisk-image"]) == 0
    assert capsys.readouterr().out.strip() == IMAGE


def test_cache_volume_flag_prints_name(monkeypatch, capsys):
    monkeypatch.setattr(docker, "check_docker_available", lambda: pytest.fail("no docker"))
    assert main(["--dazelisk-cache-volume"]) == 0
    assert capsys.readouterr().out.strip().startswith("dazelisk-cache-")


def test_forwarded_command_runs_bazelisk_and_returns_exit_code(runnable):
    assert main(["build", "//..."]) == 7
    assert runnable["command"] == ["bazelisk", "build", "//..."]
    assert runnable["tty"] is None  # auto-detected downstream


def test_shell_runs_interactive_bash_with_tty(runnable):
    assert main(["--dazelisk-shell"]) == 7
    assert runnable["command"] == ["/bin/bash", "-i"]
    assert runnable["tty"] is True


def test_as_root_is_propagated(runnable):
    main(["--dazelisk-as-root", "build"])
    assert runnable["as_root"] is True


def test_shell_with_forwarded_args_raises(runnable):
    with pytest.raises(UsageError):
        main(["--dazelisk-shell", "build"])


def test_no_command_does_nothing(runnable, monkeypatch):
    monkeypatch.setattr(container, "ensure_container", lambda *a: pytest.fail("must not create"))
    assert main([]) == 0


def test_container_restart_removes_container(monkeypatch, tmp_path):
    monkeypatch.setenv("DAZELISK_IMAGE", IMAGE)
    monkeypatch.setattr(docker, "check_docker_available", lambda: None)
    monkeypatch.setattr(workspace, "get_worktree_root", lambda: tmp_path)
    removed = []
    monkeypatch.setattr(docker, "remove_container", lambda name: removed.append(name))
    assert main(["--dazelisk-container-restart"]) == 0
    assert len(removed) == 1


def test_prune_invokes_prune(monkeypatch):
    monkeypatch.setattr(docker, "check_docker_available", lambda: None)
    called = []
    monkeypatch.setattr(docker, "prune_containers", lambda uid: called.append(uid))
    assert main(["--dazelisk-prune"]) == 0
    assert called


def test_run_reports_missing_image_cleanly(monkeypatch, capsys):
    def boom():
        raise MissingImageError("nope")

    monkeypatch.setattr(cli, "main", boom)
    with pytest.raises(SystemExit) as exc:
        run()
    assert exc.value.code == 1
    assert "dazelisk: error: nope" in capsys.readouterr().err
