# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Martino Pilia

"""dazelisk - run bazelisk transparently inside a Docker container.

Usage:
  dazelisk [DAZELISK FLAGS] [BAZELISK ARGS...]

Any argument that is not a --dazelisk-* flag is forwarded verbatim to bazelisk
inside the container, e.g. `dazelisk build //...` runs `bazelisk build //...`.

### Behavior
  - --dazelisk-shell may not be combined with forwarded bazelisk arguments.
  - --dazelisk-container-restart only removes the container; it is recreated
    implicitly by the next command (in this invocation or a later one).
  - The exit code of the forwarded command (or shell) becomes dazelisk's exit
    code.
  - A TTY is allocated only when stdin and stdout are both terminals;
    --dazelisk-shell always allocates one.

### Environment Variables
  DAZELISK_IMAGE (optional)
    Override the bundled default image. Use an immutable reference, preferably
    a pinned @sha256 digest, so the build environment stays reproducible.
      export DAZELISK_IMAGE=docker.io/myorg/my-bazel-image:1.2.3
      export DAZELISK_IMAGE=docker.io/myorg/my-bazel-image@sha256:0a1b2c3d4e5f...

  DAZELISK_MOUNTS
    JSON list of `docker run --mount` specs (applied only when the container is
    created). The example bind-mounts /data read-only and adds a scratch volume.
      export DAZELISK_MOUNTS='[
          "type=bind,src=/data,dst=/data,ro",
          "type=volume,target=/scratch"
      ]'

  DAZELISK_ENVIRONMENT
    JSON list of "NAME" (forward the host value, which never hits the command
    line) or "NAME=value" (literal) entries.
      export DAZELISK_ENVIRONMENT='["MY_SECRET", "MY_TOGGLE=on"]'

  DAZELISK_PORTS
    JSON list of `docker run -p` specs. The example publishes 80->8080,
    90->9000 on a specific host IP, and UDP 95->9500.
      export DAZELISK_PORTS='[
          "8080:80",
          "192.168.1.100:9000:90",
          "9500:95/udp"
      ]'

  DAZELISK_GPU_PASSTHROUGH
    1/0 or true/false (default: enabled) - toggles NVIDIA GPU passthrough when
    hardware and the NVIDIA container toolkit are present.
      export DAZELISK_GPU_PASSTHROUGH=0

  DAZELISK_WORKTREE_MARKERS
    JSON list of filenames marking the worktree root, overriding the default
    search of MODULE.bazel, WORKSPACE, then .bazelrc.
      export DAZELISK_WORKTREE_MARKERS='["MODULE.bazel", ".git"]'
"""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys
from pathlib import Path

from dazelisk import container, docker, naming, volume, workspace
from dazelisk.docker import DockerUnavailableError
from dazelisk.naming import MissingImageError
from dazelisk.utils import HostUser, _run_subprocess, get_host_user

logger = logging.getLogger("dazelisk")

LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class UsageError(RuntimeError):
    """Invalid combination of dazelisk command-line options."""


def parse_args(argv: list[str]) -> tuple[argparse.Namespace, list[str]]:
    parser = argparse.ArgumentParser(
        prog="dazelisk",
        description=__doc__,
        add_help=False,
        allow_abbrev=False,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--dazelisk-help",
        action="store_true",
        help="show this help and exit (--help is forwarded to bazelisk)",
    )
    parser.add_argument(
        "--dazelisk-image",
        action="store_true",
        help="print the configured image reference and exit",
    )
    parser.add_argument(
        "--dazelisk-cache-volume",
        action="store_true",
        help="print the cache volume name and exit",
    )
    parser.add_argument(
        "--dazelisk-as-root",
        action="store_true",
        help="run this invocation's command as root (0:0)",
    )
    parser.add_argument(
        "--dazelisk-prune",
        action="store_true",
        help="remove all of this user's dazelisk containers and exit",
    )
    parser.add_argument(
        "--dazelisk-mount-cache",
        action="store_true",
        help="Linux only: bind-mount the cached Bazel output onto ~/.cache/bazel "
        "for host-side inspection (uses sudo), then exit",
    )
    parser.add_argument(
        "--dazelisk-shell",
        action="store_true",
        help="open an interactive shell in the container",
    )
    parser.add_argument(
        "--dazelisk-container-restart",
        action="store_true",
        help="remove the container (recreated implicitly on the next command)",
    )
    parser.add_argument(
        "--dazelisk-log-level",
        default="WARNING",
        choices=LOG_LEVELS,
        help="logging threshold (default: %(default)s); logs go to stderr",
    )
    args, forwarded = parser.parse_known_args(argv)
    if args.dazelisk_help:
        parser.print_help()
        raise SystemExit(0)
    return args, forwarded


def setup_logging(level: str) -> None:
    logging.basicConfig(
        stream=sys.stderr,
        level=getattr(logging, level),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def _mount_cache_on_host(user: HostUser) -> int:
    """Bind-mount the volume's Bazel cache onto ~/.cache/bazel (Linux only)."""
    if sys.platform == "darwin":
        logger.error(
            "--dazelisk-mount-cache is not supported on macOS: the cache volume "
            "lives inside the Docker Desktop VM and has no host-reachable path."
        )
        return 1
    cache_volume = naming.get_volume_name(user.uid)
    if not volume.volume_exists(cache_volume):
        logger.error("cache volume %s does not exist yet; run a build first", cache_volume)
        return 1
    source = Path(volume.get_volume_mountpoint(cache_volume)) / "bazel"
    if not source.exists():
        logger.error("no Bazel cache found at %s yet; run a build first", source)
        return 1
    destination = Path(user.home) / ".cache" / "bazel"
    destination.mkdir(parents=True, exist_ok=True)
    logger.info("bind-mounting %s onto %s (requires sudo)", source, destination)
    _run_subprocess(["sudo", "mount", "--bind", str(source), str(destination)])
    print(f"Mounted Bazel cache at {destination}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args, forwarded = parse_args(sys.argv[1:] if argv is None else argv)
    setup_logging(args.dazelisk_log_level)

    if args.dazelisk_image:
        print(naming.get_image_name())
        return 0

    user = get_host_user()
    if args.dazelisk_cache_volume:
        print(naming.get_volume_name(user.uid))
        return 0

    docker.check_docker_available()

    if args.dazelisk_prune:
        docker.prune_containers(user.uid)
        return 0

    if args.dazelisk_mount_cache:
        return _mount_cache_on_host(user)

    if args.dazelisk_shell and forwarded:
        raise UsageError("--dazelisk-shell cannot be combined with forwarded bazelisk arguments")

    worktree = workspace.get_worktree_root()
    names = naming.ResourceNames.build(naming.get_image_name(), user.uid, worktree)

    if args.dazelisk_container_restart:
        docker.remove_container(names.container)

    if not (args.dazelisk_shell or forwarded):
        return 0

    container.ensure_container(names, user)
    if args.dazelisk_shell:
        return container.run_in_container(
            names.container,
            ["/bin/bash", "-i"],
            as_root=args.dazelisk_as_root,
            tty=True,
        )
    return container.run_in_container(
        names.container, ["bazelisk", *forwarded], as_root=args.dazelisk_as_root
    )


def run() -> None:
    try:
        sys.exit(main())
    except (
        MissingImageError,
        DockerUnavailableError,
        UsageError,
        ValueError,
        subprocess.CalledProcessError,
    ) as exc:
        print(f"dazelisk: error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    run()
