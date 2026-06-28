# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Martino Pilia

import pytest

from dazelisk import gpu
from dazelisk.gpu import _passthrough_requested, should_enable_gpus


@pytest.mark.parametrize("value", ["1", "true", "TRUE", " True "])
def test_passthrough_requested_truthy(value):
    assert _passthrough_requested(value) is True


@pytest.mark.parametrize("value", ["0", "false", "FALSE", " false "])
def test_passthrough_requested_falsy(value):
    assert _passthrough_requested(value) is False


def test_passthrough_requested_default_enabled():
    assert _passthrough_requested(None) is True


@pytest.mark.parametrize("value", ["", "yes", "no", "2", "on"])
def test_passthrough_requested_invalid_raises(value):
    with pytest.raises(ValueError):
        _passthrough_requested(value)


def test_disabled_env_short_circuits_detection(monkeypatch):
    monkeypatch.setattr(gpu, "has_nvidia_gpu", lambda: pytest.fail("must not probe"))
    assert should_enable_gpus({"DAZELISK_GPU_PASSTHROUGH": "0"}) is False


def test_enabled_only_when_gpu_and_toolkit_present(monkeypatch):
    monkeypatch.setattr(gpu, "has_nvidia_gpu", lambda: True)
    monkeypatch.setattr(gpu, "has_nvidia_container_cli", lambda: True)
    assert should_enable_gpus({}) is True


def test_disabled_when_toolkit_missing(monkeypatch):
    monkeypatch.setattr(gpu, "has_nvidia_gpu", lambda: True)
    monkeypatch.setattr(gpu, "has_nvidia_container_cli", lambda: False)
    assert should_enable_gpus({}) is False


def test_disabled_when_no_gpu(monkeypatch):
    monkeypatch.setattr(gpu, "has_nvidia_gpu", lambda: False)
    monkeypatch.setattr(gpu, "has_nvidia_container_cli", lambda: True)
    assert should_enable_gpus({}) is False


def test_invalid_env_propagates(monkeypatch):
    with pytest.raises(ValueError):
        should_enable_gpus({"DAZELISK_GPU_PASSTHROUGH": "maybe"})
