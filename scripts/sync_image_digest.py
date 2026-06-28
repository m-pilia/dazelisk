#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Martino Pilia

"""Pin or verify the default image digest in src/dazelisk/default_image.json.

The image build is reproducible (pinned inputs + SOURCE_DATE_EPOCH=0), so the
digest is deterministic and known before any push.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
IMAGE_DIR = REPO_ROOT / "image"
DATA_FILE = REPO_ROOT / "src" / "dazelisk" / "default_image.json"
INDEX_TARGET = "//:index"


def _build_index_digest(bazel: str) -> str:
    subprocess.run([bazel, "build", INDEX_TARGET], cwd=IMAGE_DIR, check=True)
    index_json = IMAGE_DIR / "bazel-bin" / "index" / "index.json"
    manifest = json.loads(index_json.read_text())
    return manifest["manifests"][0]["digest"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify the stored digest matches the built one instead of writing",
    )
    parser.add_argument(
        "--bazel",
        default="bazelisk",
        help="Bazel launcher to use (default: bazelisk)",
    )
    args = parser.parse_args(argv)

    digest = _build_index_digest(args.bazel)
    data = json.loads(DATA_FILE.read_text())

    if args.check:
        if data["digest"] != digest:
            print(
                f"default image digest is out of date in {DATA_FILE.name}:\n"
                f"  expected: {digest}\n"
                f"  found:    {data['digest'] or '(unset)'}\n"
                "Run: python scripts/sync_image_digest.py",
                file=sys.stderr,
            )
            return 1
        print(f"default image digest is up to date ({digest})")
        return 0

    data["digest"] = digest
    DATA_FILE.write_text(json.dumps(data, indent=2) + "\n")
    print(f"wrote {data['repo']}@{digest} to {DATA_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
