# dazelisk design guidelines

Standing, long-term guidance for working on dazelisk. Optimised for LLM
consumption: principles only, no walkthrough of what the code already says, no
one-off task notes.

## Scope and invariants

- dazelisk is a thin wrapper that runs bazelisk inside a Docker container.
- Pure Python standard library only — no third-party runtime dependencies.
- dazelisk ships a default image, `martinopilia/dazelisk` on Docker Hub, pinned
  to an immutable reference (a tag or digest baked into dazelisk, never a mutable
  tag like `:latest`). `DAZELISK_IMAGE` optionally overrides it; an override
  should likewise be immutable, for reproducibility and supply-chain safety. The
  baked default is updated deliberately per release.
- Every host-side resource is scoped to be safe on multi-user hosts and across
  multiple checkouts. Containers, passwd/group files, and the worktree lock are
  keyed by UID and a 10-char SHA-256 of the worktree root; the cache volume is
  keyed by UID only (deliberately shared across a user's worktrees).
- dazelisk never builds, bootstraps, or pushes the image — it only pulls it.

## Language level

- Target Python 3.12+. Prefer modern idioms (`match`, builtin generics,
  `X | None`, `pathlib`, dataclasses, structural patterns) over verbose
  backward-compatible constructs.

## Tooling

- Lint with `ruff check`, format with `ruff format`, and type-check with
  `ty check`; all must pass on `src` and `tests`. Configuration lives in
  `pyproject.toml`, and CI enforces all three (plus `ruff format --check`).
- Formatting is owned by `ruff format`, so the linter does not flag line length
  (`E501` is disabled). Keep the code formatter-clean.
- In the Docker argument builders, prefer the combined `--flag=value` form
  (single list element) over separate `"--flag", value` pairs, so each argument
  stays on one line and reads well under the formatter.

## Subprocess discipline

- All process execution goes through `utils._run_subprocess`. No raw
  `subprocess.run`/`check_output`/`Popen` in module logic.
- Arguments are always a list; never `shell=True`; never interpolate
  user/secret values into a shell string.
- `_run_subprocess` times each call and logs it at DEBUG, so the whole tool is
  trivially profilable.

## Docker invocation

- Always use long-form flags (`--env`, `--publish`, `--mount`, `--volume`,
  `--user`, `--label`), never short aliases.
- Container creation is the only place mounts, ports, environment, GPU, and
  platform take effect; `docker exec` never re-applies them.
- Discover a user's containers via the `dazelisk.uid=<uid>` label, not by
  parsing names.

## Concurrency

- The image/volume/container ensure-and-create section is serialised by a
  per-worktree advisory file lock (`flock`). The lock is released before the
  long-running `docker exec`, so concurrent commands in the same worktree still
  run in parallel once the container exists.

## Logging

- Use the `logging` module; all output goes to stderr so forwarded bazelisk
  stdout is never corrupted. Most tracing is INFO/DEBUG; default threshold is
  WARNING. GPU detection/enablement is logged at INFO.

## Error handling

- Fail loudly and early on misconfiguration (malformed `DAZELISK_*` JSON,
  invalid `DAZELISK_GPU_PASSTHROUGH`). Never silently degrade to an empty
  configuration.
- Surface actionable guidance for environmental failures (Docker missing, daemon
  down, permission denied).

## Runtime image contract

- The default image (`martinopilia/dazelisk`) is built separately with Bazel +
  rules_oci + rules_distroless and published to Docker Hub; it is not built by
  dazelisk at runtime.
- It is a minimal *distroless-based* image, not an empty distroless one. It must
  still provide what dazelisk relies on at runtime: a shell (`/bin/bash` for
  `--dazelisk-shell`), `sleep` (keep-alive entrypoint), and `chown` (cache-volume
  permission fix), plus bazelisk itself — and nothing beyond what is strictly
  necessary.
- Multi-arch (`linux/amd64` + `linux/arm64`) so Docker pulls the host-matching
  architecture; dazelisk performs no platform forcing.

## Image build & release

- The image lives in the self-contained Bazel workspace under `image/`
  (`rules_oci` + `rules_distroless`), decoupled from the Python package; the repo
  root stays Bazel-free.
- Base is Debian distroless *static* (no libc); glibc, bash, coreutils, and the
  C++/zlib runtimes Bazel needs come from the apt closure, pinned via
  `image/packages.lock.json` against a fixed `snapshot.debian.org` timestamp.
  Only bazelisk is baked in; Bazel is downloaded at runtime.
- Reproducible by construction: base pinned by digest, apt lockfile, bazelisk
  pinned by sha256, and `SOURCE_DATE_EPOCH=0` with fixed layer mtimes. The
  multi-arch index digest is therefore deterministic and known before any push.
- The default image is pinned **by digest** in the bundled data file
  `src/dazelisk/default_image.json`, managed by `scripts/sync_image_digest.py`
  (`--write` to update, `--check` to verify). Never hand-edit the digest.
- Versions are synced: the image tag equals the package version. CI publishes
  both together (image to Docker Hub, package to PyPI) when `pyproject.toml`'s
  `version` changes on `main` — no git release tags. The pinned digest is
  verified in CI (`--check`) before publishing and re-checked against the pushed
  remote digest, so the source pin is never mutated inside the workflow.

## Security considerations

- **Shell injection**: prevented structurally by `_run_subprocess` (list args,
  never `shell=True`).
- **Secrets in the process list**: forward host variables by name (`--env NAME`)
  so Docker resolves the value out-of-band; values are never placed on a command
  line.
- **Secrets via `docker inspect`**: accepted residual exposure. `--env NAME`
  values are stored in the container config and readable via `docker inspect` /
  `/proc/1/environ` for the container's lifetime. Callers decide what to forward.
- **Temp files**: passwd/group files are written `0600`. They contain no
  secrets and are intentionally not cleaned up (they must outlive a single
  invocation because the container is reused; `/tmp` reaping handles them).
- **Docker history**: no secret value is ever passed on a `docker run`/`exec`
  command line.

## Testing guidelines

- Test observable behavior through the public API, never internals or
  implementation details.
- Favor quality over quantity; do not assert on incidental details coupled to
  the implementation.
- Use mocks only to cut genuine external dependencies (the Docker CLI,
  `nvidia-smi`, the host environment). Never use mocks to probe internal calls,
  and avoid them where a real, cheap substitute (tmp dirs, real parsing) works.
- Prefer extracting pure functions (e.g. command-line builders) so they can be
  tested directly without any mocking.
- Write tests alongside the module they cover, not as a separate final phase.
- `pytest` (+ `pytest-mock` only where unavoidable); gate Docker-dependent tests
  with `pytest.mark.skipif`.
