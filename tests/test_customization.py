# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Martino Pilia

import pytest

from dazelisk.customization import parse_environment, parse_mounts, parse_ports


@pytest.mark.parametrize("value", [None, "", "   ", "[]"])
def test_empty_inputs_yield_empty_list(value):
    assert parse_mounts(value) == []
    assert parse_ports(value) == []
    assert parse_environment(value, {}) == []


def test_parse_mounts_returns_specs():
    value = '["type=bind,src=/data,dst=/data,ro", "type=volume,target=/w"]'
    assert parse_mounts(value) == [
        "type=bind,src=/data,dst=/data,ro",
        "type=volume,target=/w",
    ]


def test_parse_ports_returns_specs():
    assert parse_ports('["8080:80", "9500:95/udp"]') == ["8080:80", "9500:95/udp"]


def test_invalid_json_raises():
    with pytest.raises(ValueError, match="not valid JSON"):
        parse_mounts("[not json")


def test_non_list_raises():
    with pytest.raises(ValueError, match="list of strings"):
        parse_ports('{"a": 1}')


def test_non_string_elements_raise():
    with pytest.raises(ValueError, match="list of strings"):
        parse_mounts("[1, 2]")


def test_environment_forwards_name_and_sets_literal():
    env = parse_environment('["MY_SECRET", "MY_TOGGLE=on"]', {"MY_SECRET": "s3cr3t"})
    assert env == ["MY_SECRET", "MY_TOGGLE=on"]


def test_environment_fails_when_forwarded_name_absent():
    with pytest.raises(ValueError, match="not set on the host"):
        parse_environment('["MISSING"]', {})


def test_environment_allows_absent_name_with_literal_value():
    assert parse_environment('["MISSING=x"]', {}) == ["MISSING=x"]


def test_environment_empty_name_raises():
    with pytest.raises(ValueError, match="empty variable name"):
        parse_environment('["=value"]', {})
