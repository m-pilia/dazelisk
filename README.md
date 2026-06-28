# dazelisk

**dazelisk** (portmanteau of *Docker* + *Bazelisk*) is a containerized
[bazelisk](https://github.com/bazelbuild/bazelisk) wrapper focused on
simplicity and supply chain safety, targeting modern Bazel versions, that aims
to isolate and normalize the build environment across machines and platforms by
providing a transparent containerized wrapping of Bazel invocations.

In place of

```sh
bazelisk build //...
```

you run

```sh
dazelisk build //...
```

and the command executes transparently inside a Linux Docker container, giving a
consistent build environment across Linux, WSL2, and macOS (Apple Silicon only).

Any argument that is not a `--dazelisk-*` flag is forwarded verbatim to bazelisk.

## Supported platforms

- Linux
- macOS (Apple silicon only)
- Windows (WSL2 only)

## Requirements

- Python 3.12+
- Docker (Engine on Linux/WSL2, Desktop on macOS) with a running daemon
- The `DAZELISK_IMAGE` environment variable (see below)

dazelisk has **no third-party Python dependencies** to strengthen supply chain
safety.

## Installation

```sh
uv pip install dazelisk
```

This installs the `dazelisk` entry point.

## `DAZELISK_IMAGE` is mandatory

dazelisk does not build or bundle an image; it only pulls one. You must point it
at an image via `DAZELISK_IMAGE`:

```sh
export DAZELISK_IMAGE=docker.io/library/dazelisk:1.0.0-1
# or pin a digest for exact reproducibility:
export DAZELISK_IMAGE=docker.io/library/dazelisk@sha256:<digest>
```

There is **no default on purpose**: the reference must be immutable (a pinned
tag or a digest). Mutable tags such as `:latest` would silently change the build
environment, undermining reproducibility and supply-chain safety. dazelisk fails
immediately with guidance if `DAZELISK_IMAGE` is unset.

## Usage

```sh
dazelisk build //...
dazelisk test //foo:bar --config=ci
dazelisk --dazelisk-shell                 # interactive shell in the container
dazelisk --dazelisk-as-root run //tool    # run this command as root
```

### Supported arguments and environment variables

See
```
dazelisk --dazelisk-help
```

## Cache

A per-user Docker volume (`dazelisk-cache-<uid>`) is mounted at `$HOME/.cache`
inside the container and shared across all of your worktrees. A volume (rather
than a bind mount) avoids cross-platform permission issues and gives native
Linux filesystem performance on macOS.

## GPU passthrough

If an NVIDIA GPU and the NVIDIA Container Toolkit (`nvidia-container-cli`) are
both present, dazelisk adds `--gpus all` automatically. Disable with
`DAZELISK_GPU_PASSTHROUGH=0`.

## Container naming & isolation

Containers are scoped by image, user and worktree to avoid collisions, and
changing `DAZELISK_IMAGE` automatically uses a fresh container.

## Troubleshooting

- **`DAZELISK_IMAGE is not set`** — export it (see above).
- **Docker CLI not found / daemon not reachable** — install Docker and start it
  (`sudo systemctl start docker`, or launch Docker Desktop).
- **Permission denied talking to Docker** — `sudo usermod -aG docker $USER && newgrp docker`.
- **Invalid `DAZELISK_*` JSON** — dazelisk reports the parse error; fix the JSON.
- **`--dazelisk-mount-cache` on macOS** — unsupported; the volume lives inside
  the Docker Desktop VM with no host-reachable path.

## Development

```sh
uv run pytest
```

See `DESIGN.md` for design and security guidelines.

## Related projects

- [dazel](https://github.com/nadirizr/dazel) — A transparent proxy that runs
  Bazel commands inside a Docker container.

## License

dazelisk is released under the MIT License. See [LICENSE](LICENSE).
