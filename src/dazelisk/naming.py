# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Martino Pilia

"""Resource naming and scoping by UID and worktree SHA."""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path

WORKTREE_SHA_LENGTH = 10
IMAGE_IDENTIFIER_LENGTH = 10

TEMP_DIR = Path("/tmp")

IMAGE_ENV_VAR = "DAZELISK_IMAGE"
UID_LABEL_KEY = "dazelisk.uid"


class MissingImageError(RuntimeError):
    """Raised when the mandatory DAZELISK_IMAGE variable is not set."""


def get_image_name() -> str:
    image = os.environ.get(IMAGE_ENV_VAR)
    if not image:
        raise MissingImageError(
            f"{IMAGE_ENV_VAR} is not set. It is mandatory and must reference an "
            "immutable image (a pinned tag or a digest), e.g.\n"
            f"  export {IMAGE_ENV_VAR}=docker.io/library/dazelisk:1.0.0-1\n"
            f"  export {IMAGE_ENV_VAR}=docker.io/library/dazelisk@sha256:<digest>\n"
            "No default is provided on purpose: mutable tags would undermine "
            "reproducibility and supply-chain safety."
        )
    return image


def _sha10(value: str, length: int) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:length]


def get_image_identifier(image_name: str) -> str:
    return _sha10(image_name, IMAGE_IDENTIFIER_LENGTH)


def get_worktree_sha(worktree_root: Path | str) -> str:
    return _sha10(str(worktree_root), WORKTREE_SHA_LENGTH)


def get_container_name(image_name: str, uid: int, worktree_sha: str) -> str:
    return f"dazelisk-{get_image_identifier(image_name)}-{uid}-{worktree_sha}"


def get_volume_name(uid: int) -> str:
    return f"dazelisk-cache-{uid}"


def uid_label(uid: int) -> str:
    return f"{UID_LABEL_KEY}={uid}"


@dataclass(frozen=True)
class ResourceNames:
    image: str
    uid: int
    worktree_root: Path
    worktree_sha: str
    container: str
    volume: str
    lock_path: Path

    @classmethod
    def build(cls, image: str, uid: int, worktree_root: Path | str) -> ResourceNames:
        worktree_root = Path(worktree_root)
        worktree_sha = get_worktree_sha(worktree_root)
        return cls(
            image=image,
            uid=uid,
            worktree_root=worktree_root,
            worktree_sha=worktree_sha,
            container=get_container_name(image, uid, worktree_sha),
            volume=get_volume_name(uid),
            lock_path=TEMP_DIR / f"dazelisk-{uid}-{worktree_sha}.lock",
        )
