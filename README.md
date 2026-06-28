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

dazelisk has **no third-party Python dependencies** to strengthen supply chain
safety.

## Installation

```sh
uv pip install dazelisk
```

This installs the `dazelisk` entry point.

## Container image

The container image can be configured. By default dazelisk uses the official
image published on Docker Hub,
[`martinopilia/dazelisk`](https://hub.docker.com/r/martinopilia/dazelisk) — a
minimal image containing only what is needed to run bazelisk, so that you do
not pay for what you do not use. It is pulled automatically on first use; no
configuration is required. dazelisk never builds an image, it only pulls one.

To use a custom image instead, set `DAZELISK_IMAGE`:

```sh
# pin a digest for exact reproducibility
export DAZELISK_IMAGE=docker.io/myorg/my-bazel-image@sha256:<digest>
```

For reproducibility and supply-chain safety, a custom `DAZELISK_IMAGE` should
also be an immutable reference (a pinned tag or a digest), not a mutable tag.

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

- **Image pull failure** — check your network/registry access and that
  `DAZELISK_IMAGE` (if set) is a valid, reachable reference.
- **Docker CLI not found / daemon not reachable** — install Docker and start it
  (`sudo systemctl start docker`, or launch Docker Desktop).
- **Permission denied talking to Docker** — `sudo usermod -aG docker $USER && newgrp docker`.
- **Invalid `DAZELISK_*` JSON** — dazelisk reports the parse error; fix the JSON.
- **`--dazelisk-mount-cache` on macOS** — unsupported; the volume lives inside
  the Docker Desktop VM with no host-reachable path.

## Development

See `DESIGN.md` for design and security guidelines.

Run checks and tests:

```sh
./pre_push.sh
```

Or individually:

```sh
uv run pytest              # tests
uv run ruff check          # lint
uv run ruff format         # auto-format the code
uv run ruff format --check # verify formatting
uv run ty check            # type-check
```

Build and load the image:

```
cd image
bazelisk test //...                 # build the image and run its tests
bazelisk run //:load                # load it into the local Docker daemon
```

Manual push to registry:

```
bazelisk run //:push -- --repository <repository> --tag <tag>
```

After changing anything under `image/`, refresh the pinned default digest:

```sh
python scripts/sync_image_digest.py           # rewrite the pinned digest
python scripts/sync_image_digest.py --check   # verify if the digest is up to date
```

To add a Debian package, edit `image/packages.yaml` and regenerate the lock:

```sh
cd image
bazelisk run @bookworm//:lock
```

## Related projects

- [dazel](https://github.com/nadirizr/dazel) — A transparent proxy that runs
  Bazel commands inside a Docker container.

## License

dazelisk is released under the MIT License. See [LICENSE](LICENSE).
