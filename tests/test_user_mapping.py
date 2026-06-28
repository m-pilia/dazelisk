# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Martino Pilia

import stat

from dazelisk.user_mapping import (
    generate_group,
    generate_passwd,
    write_passwd_group,
)
from dazelisk.utils import HostUser

USER = HostUser(uid=1000, gid=1000, username="alice", groupname="devs", home="/home/alice")


def test_passwd_has_root_and_host_user_with_forwarded_home():
    content = generate_passwd(USER)
    lines = content.splitlines()
    assert lines[0].startswith("root:x:0:0:")
    assert "alice:x:1000:1000:alice:/home/alice:" in content


def test_group_has_root_and_primary_group_only():
    content = generate_group(USER)
    assert "root:x:0:" in content
    assert "devs:x:1000:" in content
    assert content.count("\n") == 2


def test_write_creates_both_files_with_0600(tmp_path):
    passwd, group = write_passwd_group(USER, "abc123", temp_dir=tmp_path)
    for path in (passwd, group):
        assert path.exists()
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert passwd.read_text() == generate_passwd(USER)
    assert group.read_text() == generate_group(USER)


def test_write_paths_are_scoped_by_uid_and_worktree(tmp_path):
    passwd, group = write_passwd_group(USER, "abc123", temp_dir=tmp_path)
    assert passwd.name == "dazelisk-passwd-1000-abc123"
    assert group.name == "dazelisk-group-1000-abc123"


def test_write_overwrites_and_resets_permissions(tmp_path):
    passwd = tmp_path / "dazelisk-passwd-1000-abc123"
    passwd.write_text("stale")
    passwd.chmod(0o644)
    write_passwd_group(USER, "abc123", temp_dir=tmp_path)
    assert passwd.read_text() == generate_passwd(USER)
    assert stat.S_IMODE(passwd.stat().st_mode) == 0o600
