#!/usr/bin/env bash

set -euo pipefail

uv run pytest
uv run ruff check
uv run ruff format
uv run ruff format --check
uv run ty check

(
cd image
bazelisk test //...
)
