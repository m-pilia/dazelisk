# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Martino Pilia

import hashlib
from pathlib import Path

import pytest

from dazelisk.naming import (
    IMAGE_IDENTIFIER_LENGTH,
    WORKTREE_SHA_LENGTH,
    MissingImageError,
    ResourceNames,
    get_container_name,
    get_image_identifier,
    get_image_name,
    get_volume_name,
    get_worktree_sha,
    uid_label,
)

IMAGE = "docker.io/library/dazelisk:1.0.0-1"


def test_get_image_name_raises_when_unset(monkeypatch):
    monkeypatch.delenv("DAZELISK_IMAGE", raising=False)
    with pytest.raises(MissingImageError):
        get_image_name()


def test_get_image_name_returns_value(monkeypatch):
    monkeypatch.setenv("DAZELISK_IMAGE", IMAGE)
    assert get_image_name() == IMAGE


def test_image_identifier_is_truncated_sha_of_reference():
    expected = hashlib.sha256(IMAGE.encode()).hexdigest()[:IMAGE_IDENTIFIER_LENGTH]
    assert get_image_identifier(IMAGE) == expected
    assert len(get_image_identifier(IMAGE)) == IMAGE_IDENTIFIER_LENGTH


def test_different_images_yield_different_identifiers():
    assert get_image_identifier(IMAGE) != get_image_identifier(IMAGE + "x")


def test_worktree_sha_length():
    assert len(get_worktree_sha("/home/u/repo")) == WORKTREE_SHA_LENGTH


def test_volume_name_is_per_user_only():
    assert get_volume_name(1000) == "dazelisk-cache-1000"


def test_uid_label():
    assert uid_label(1000) == "dazelisk.uid=1000"


def test_container_name_layout():
    name = get_container_name(IMAGE, 1000, "a1b2c3d4e5")
    assert name == f"dazelisk-{get_image_identifier(IMAGE)}-1000-a1b2c3d4e5"


def test_resource_names_build():
    names = ResourceNames.build(IMAGE, 1000, "/home/u/repo")
    assert names.container == get_container_name(IMAGE, 1000, names.worktree_sha)
    assert names.volume == "dazelisk-cache-1000"
    assert names.lock_path.name == f"dazelisk-1000-{names.worktree_sha}.lock"
    assert names.worktree_root == Path("/home/u/repo")


def test_container_name_changes_with_image_isolating_versions():
    a = ResourceNames.build(IMAGE, 1000, "/repo").container
    b = ResourceNames.build(IMAGE + "-next", 1000, "/repo").container
    assert a != b
