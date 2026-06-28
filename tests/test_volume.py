# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Martino Pilia

from dazelisk.volume import _permission_fix_args


def test_permission_fix_runs_chown_as_root_on_mounted_volume():
    args = _permission_fix_args("dazelisk-cache-1000", 1000, 1000, "img:1")
    assert args[:2] == ["docker", "run"]
    assert "--rm" in args
    assert args[args.index("--user") + 1] == "0:0"
    assert args[args.index("--entrypoint") + 1] == "chown"
    assert "dazelisk-cache-1000:/cache" in args
    assert args[-3:] == ["img:1", "1000:1000", "/cache"]
