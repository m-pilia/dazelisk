# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Martino Pilia

import pytest

from dazelisk.workspace import get_worktree_root


def test_detects_module_bazel_from_subdir(tmp_path):
    (tmp_path / "MODULE.bazel").touch()
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    assert get_worktree_root(nested) == tmp_path


def test_prefers_nearest_ancestor_marker(tmp_path):
    (tmp_path / "MODULE.bazel").touch()
    inner = tmp_path / "inner"
    inner.mkdir()
    (inner / ".bazelrc").touch()
    nested = inner / "deep"
    nested.mkdir()
    assert get_worktree_root(nested) == inner


def test_workspace_marker_is_honoured_but_not_required(tmp_path):
    (tmp_path / "WORKSPACE").touch()
    assert get_worktree_root(tmp_path) == tmp_path


def test_falls_back_to_start_directory_without_markers(tmp_path):
    nested = tmp_path / "x"
    nested.mkdir()
    assert get_worktree_root(nested) == nested


def test_custom_markers_override_defaults(tmp_path):
    (tmp_path / "my.root").touch()
    nested = tmp_path / "a"
    nested.mkdir()
    env = {"DAZELISK_WORKTREE_MARKERS": '["my.root"]'}
    assert get_worktree_root(nested, env=env) == tmp_path


def test_default_markers_ignored_when_overridden(tmp_path):
    (tmp_path / "MODULE.bazel").touch()
    nested = tmp_path / "a"
    nested.mkdir()
    env = {"DAZELISK_WORKTREE_MARKERS": '["my.root"]'}
    # MODULE.bazel is no longer a marker, so detection falls back to start.
    assert get_worktree_root(nested, env=env) == nested


def test_invalid_markers_json_raises(tmp_path):
    with pytest.raises(ValueError, match="not valid JSON"):
        get_worktree_root(tmp_path, env={"DAZELISK_WORKTREE_MARKERS": "[bad"})


def test_empty_markers_list_raises(tmp_path):
    with pytest.raises(ValueError, match="at least one marker"):
        get_worktree_root(tmp_path, env={"DAZELISK_WORKTREE_MARKERS": "[]"})
