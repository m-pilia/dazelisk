# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Martino Pilia

"""Parsing of the DAZELISK_MOUNTS / DAZELISK_ENVIRONMENT / DAZELISK_PORTS vars.

All parsers fail loudly (raise ``ValueError``) on malformed input rather than
silently degrading to an empty configuration.
"""

from __future__ import annotations

import json
from collections.abc import Mapping


def parse_json_string_list(value: str | None, var_name: str) -> list[str]:
    """Parse an optional DAZELISK_* env var holding a JSON list of strings."""
    if value is None or value.strip() == "":
        return []
    try:
        data = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{var_name} is not valid JSON: {exc}") from exc
    if not isinstance(data, list) or not all(isinstance(item, str) for item in data):
        raise ValueError(f"{var_name} must be a JSON list of strings")
    return data


def parse_mounts(value: str | None) -> list[str]:
    """DAZELISK_MOUNTS -> list of ``docker run --mount`` spec strings."""
    return parse_json_string_list(value, "DAZELISK_MOUNTS")


def parse_ports(value: str | None) -> list[str]:
    """DAZELISK_PORTS -> list of ``docker run --publish`` spec strings."""
    return parse_json_string_list(value, "DAZELISK_PORTS")


def parse_environment(value: str | None, host_env: Mapping[str, str]) -> list[str]:
    """DAZELISK_ENVIRONMENT -> list of ``docker run --env`` arguments.

    ``"NAME"`` becomes ``NAME`` (Docker forwards the value from the host
    environment without it ever appearing on the command line); ``"NAME=value"``
    is passed through literally.
    """
    entries = parse_json_string_list(value, "DAZELISK_ENVIRONMENT")
    result: list[str] = []
    for entry in entries:
        name = entry.split("=", 1)[0]
        if not name:
            raise ValueError(
                f"DAZELISK_ENVIRONMENT entry {entry!r} has an empty variable name"
            )
        if "=" not in entry and name not in host_env:
            raise ValueError(
                f"DAZELISK_ENVIRONMENT forwards {name} but it is not set on the "
                "host; define it or use the NAME=value form"
            )
        result.append(entry)
    return result
