# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Martino Pilia

"""Worktree (Bazel repo root) detection for bzlmod / modern Bazel."""

from __future__ import annotations

import logging
import os
from collections.abc import Mapping
from pathlib import Path

from dazelisk.customization import parse_json_string_list

logger = logging.getLogger(__name__)

# Ordered markers identifying a Bazel workspace root. WORKSPACE is included for
# completeness but is never assumed to exist; bzlmod (MODULE.bazel) is preferred.
WORKTREE_MARKERS = ("MODULE.bazel", "WORKSPACE", ".bazelrc")

MARKERS_ENV_VAR = "DAZELISK_WORKTREE_MARKERS"


def _worktree_markers(env: Mapping[str, str]) -> tuple[str, ...]:
    """Markers to search for, optionally overridden by DAZELISK_WORKTREE_MARKERS."""
    override = env.get(MARKERS_ENV_VAR)
    if override is None or override.strip() == "":
        return WORKTREE_MARKERS
    markers = parse_json_string_list(override, MARKERS_ENV_VAR)
    if not markers:
        raise ValueError(f"{MARKERS_ENV_VAR} must list at least one marker")
    return tuple(markers)


def get_worktree_root(
    start: Path | None = None, env: Mapping[str, str] | None = None
) -> Path:
    """Return the worktree root by walking ancestors for a known marker.

    Falls back to the current working directory (with a warning) when no marker
    is found. Bazel is never invoked on the host.
    """
    env = os.environ if env is None else env
    markers = _worktree_markers(env)
    origin = (start or Path.cwd()).resolve()
    for directory in (origin, *origin.parents):
        for marker in markers:
            if (directory / marker).exists():
                logger.debug("worktree root %s (marker %s)", directory, marker)
                return directory
    logger.warning("no Bazel workspace marker found; falling back to %s", origin)
    return origin
