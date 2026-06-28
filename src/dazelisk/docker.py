# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Martino Pilia

"""Docker CLI abstraction. Every call goes through ``utils._run_subprocess``."""

from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass, field

from dazelisk.utils import _run_subprocess

logger = logging.getLogger(__name__)

DOCKER_CLI = "docker"


class DockerUnavailableError(RuntimeError):
    """Raised when the Docker CLI or daemon cannot be used."""


@dataclass(frozen=True)
class ContainerSpec:
    name: str
    image: str
    user: str
    home: str
    worktree: str
    cache_volume: str
    passwd_path: str
    group_path: str
    labels: dict[str, str] = field(default_factory=dict)
    extra_mounts: list[str] = field(default_factory=list)
    env_args: list[str] = field(default_factory=list)
    ports: list[str] = field(default_factory=list)
    gpus: bool = False
    entrypoint: list[str] = field(default_factory=list)


def _build_run_args(spec: ContainerSpec) -> list[str]:
    return [
        DOCKER_CLI,
        "run",
        "--detach",
        f"--name={spec.name}",
        *(f"--label={k}={v}" for k, v in spec.labels.items()),
        f"--user={spec.user}",
        f"--env=HOME={spec.home}",
        f"--volume={spec.worktree}:{spec.worktree}",
        f"--volume={spec.cache_volume}:{spec.home}/.cache",
        f"--volume={spec.passwd_path}:/etc/passwd:ro",
        f"--volume={spec.group_path}:/etc/group:ro",
        *(f"--mount={mount}" for mount in spec.extra_mounts),
        *(f"--env={env}" for env in spec.env_args),
        *(f"--publish={port}" for port in spec.ports),
        *(["--gpus=all"] if spec.gpus else []),
        spec.image,
        *spec.entrypoint,
    ]


def _build_exec_args(
    name: str,
    command: list[str],
    *,
    as_root: bool,
    interactive: bool,
    tty: bool,
    workdir: str | None,
) -> list[str]:
    return [
        DOCKER_CLI,
        "exec",
        *(["--user=0:0"] if as_root else []),
        *(["--interactive"] if interactive else []),
        *(["--tty"] if tty else []),
        *([f"--workdir={workdir}"] if workdir else []),
        name,
        *command,
    ]


def check_docker_available() -> None:
    if shutil.which(DOCKER_CLI) is None:
        raise DockerUnavailableError(
            "Docker CLI not found. dazelisk runs every command inside a Docker "
            "container, so a working Docker installation is required.\n"
            "Install Docker Engine (Linux/WSL2) or Docker Desktop (macOS) and "
            "ensure the 'docker' command is on your PATH."
        )
    result = _run_subprocess([DOCKER_CLI, "info"], check=False, capture_output=True)
    if result.returncode == 0:
        return
    stderr = (result.stderr or "").lower()
    if "permission denied" in stderr:
        raise DockerUnavailableError(
            "Permission denied talking to the Docker daemon. Add your user to "
            "the docker group:\n"
            "  sudo usermod -aG docker $USER && newgrp docker"
        )
    raise DockerUnavailableError(
        "The Docker daemon is not reachable. Make sure Docker is running "
        "(start Docker Desktop, or 'sudo systemctl start docker' on Linux)."
    )


def image_exists(image_ref: str) -> bool:
    result = _run_subprocess(
        [DOCKER_CLI, "image", "inspect", image_ref],
        check=False,
        capture_output=True,
    )
    return result.returncode == 0


def pull_image(image_ref: str) -> None:
    logger.info("pulling image %s", image_ref)
    _run_subprocess([DOCKER_CLI, "pull", image_ref])


def container_exists(name: str) -> bool:
    result = _run_subprocess(
        [DOCKER_CLI, "container", "inspect", name],
        check=False,
        capture_output=True,
    )
    return result.returncode == 0


def container_is_running(name: str) -> bool:
    result = _run_subprocess(
        [DOCKER_CLI, "container", "inspect", "--format", "{{.State.Running}}", name],
        check=False,
        capture_output=True,
    )
    return result.returncode == 0 and result.stdout.strip() == "true"


def create_container(spec: ContainerSpec) -> None:
    logger.info("creating container %s from %s", spec.name, spec.image)
    _run_subprocess(_build_run_args(spec), capture_output=True)


def exec_container(
    name: str,
    command: list[str],
    *,
    as_root: bool = False,
    interactive: bool = True,
    tty: bool = False,
    workdir: str | None = None,
) -> int:
    args = _build_exec_args(
        name, command, as_root=as_root, interactive=interactive, tty=tty, workdir=workdir
    )
    return _run_subprocess(args, check=False).returncode


def stop_container(name: str) -> None:
    if container_is_running(name):
        logger.info("stopping container %s", name)
        _run_subprocess([DOCKER_CLI, "stop", name], capture_output=True)


def remove_container(name: str) -> None:
    if container_exists(name):
        logger.info("removing container %s", name)
        _run_subprocess([DOCKER_CLI, "rm", "--force", name], capture_output=True)


def prune_containers(uid: int) -> list[str]:
    from dazelisk.naming import uid_label

    result = _run_subprocess(
        [DOCKER_CLI, "ps", "--all", "--quiet", "--filter", f"label={uid_label(uid)}"],
        capture_output=True,
    )
    ids = result.stdout.split()
    if ids:
        logger.info("removing %d container(s) for uid %s", len(ids), uid)
        _run_subprocess([DOCKER_CLI, "rm", "--force", *ids], capture_output=True)
    return ids
