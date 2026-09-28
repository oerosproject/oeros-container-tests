# oeros-container-tests

Spec-driven parity tests: do the meta-oeros ROS 2 container images (Lyrical on Yocto Wrynose)
behave like the official OSRF / Docker Hub images? Every test runs against both image families
and the result is a per-tier parity matrix, not just pass/fail.

The plan is in [`specs/ROS 2 Container Parity Test Plan.md`](specs/ROS%202%20Container%20Parity%20Test%20Plan.md).
Each documented workflow is a numbered parity spec in [`specs/`](specs/), and each test names
the criterion it checks with `@pytest.mark.spec("PS-001", "AC2")`.

## Quick start

Prerequisites: Python 3.11+, [nox](https://nox.thea.codes/), and Docker or podman (auto-detected;
set `CONTAINER_RUNTIME` to force one). Rootless podman works.

```sh
# 1. load the locally built oeros images (from the bitbake deploy dir, no skopeo needed)
python -m tools.load_oeros --tier ros-core --tier ros-base
python -m tools.load_oeros --tier dev  # oeros-container-ros-dev (3.7 GB), for PS-005

# 2. run the smoke slice against the local images
OEROS_SOURCE=local nox -s smoke

# 3. read the parity matrix
nox -s report
```

| Session | What it runs |
| --- | --- |
| `nox -s smoke` | PS-001, PS-002, PS-012 on ros-core and ros-base |
| `nox -s parity -- --tier desktop` | every spec for one tier, both families |
| `nox -s gui` | PS-011 with the Xvfb sidecar |
| `nox -s arm64 -- --tier ros-base` | the same specs under QEMU (spot checks only) |
| `nox -s ci` | the invocation GitHub Actions uses (requires pinned OSRF digests) |
| `nox -s report [-- <results dirs>]` | build the parity matrix from a run |
| `nox -s lint` | spec-lint, ruff |

Everything after `--` goes to pytest, for example `nox -s parity -- --spec PS-010 --tier ros-base -x`.
Options added by this suite: `--tier`, `--family`, `--spec` (each repeatable), `--arch`,
`--run-id`, `--results-dir`. Results land in `results/<run-id>/` (`results/latest` links to the
last run): `junit.xml`, `allure-results/`, `parity.json`, `traceability.json`, `artifacts/`.

## Environment variables

| Variable | Meaning |
| --- | --- |
| `OEROS_SOURCE` | `registry` (default) pulls from GHCR; `local` uses images loaded by `tools.load_oeros` |
| `OEROS_REGISTRY` | registry and namespace, default `ghcr.io/oerosproject` |
| `OEROS_TAG` | oeros image tag, default `lyrical-wrynose` (local images are `<tag>-<arch>`) |
| `OEROS_BUILD_DIR` | bitbake build dir for `tools.load_oeros` |
| `CONTAINER_RUNTIME` | `docker` or `podman`; default is docker if its daemon is reachable, else podman |
| `REQUIRE_PINNED_DIGESTS` | `1` refuses OSRF images without a digest in `images.yaml` (CI sets it) |

## Layout

```text
specs/          parity specs PS-NNN-*.md (front matter + numbered acceptance criteria), step-mapping.md
images.yaml     tier x family -> image ref; OSRF entries pinned by digest (tools/refresh_digests.py)
gaps.yaml       known oeros gaps: each entry makes one test a strict xfail linked to an issue
contracts/      PS-012 recorded contracts per family, PS-013 intended differences
compose/        PS-004 / PS-011 compose files (image refs from env vars)
workspaces/     PS-005 / PS-006 fixtures
tests/          conftest.py, plugins/ (options, spec traceability), runtime.py, test_psNNN_*.py
tools/          spec_lint, parity_report, matrix, load_oeros, refresh_digests
.github/        parity.yml (reusable), refresh-digests.yml (weekly)
```

## How it works

- The spec's front matter (`tiers:`) decides which tiers a test runs on; tests never name tiers.
- A test takes the `probe` fixture (command through the image's own entrypoint) or `ros`
  (same, with `/opt/ros/lyrical/setup.sh` sourced explicitly, so a spec measures its own
  capability and not the entrypoint, which PS-001 covers). Tests that compare both families in
  one body (PS-013) use `probe_for` / `ros_for`.
- Probes stick to portable shell: the oeros images use busybox utilities (`head -n 3`, not
  `head -3`; no `timeout`).
- **Pass rules.** A run fails on any unexpected failure, any strict XPASS, or any OSRF failure
  (a broken reference means a broken test). To record a known gap, add it to `gaps.yaml` with
  its meta-oeros issue; when the fix lands the strict XPASS fails the run and the entry goes.
- **Spec lifecycle.** Draft, then Approved (every criterion needs a test and a pinned
  `source_sha`, enforced by `spec-lint`), Implemented, Verified or Gap.
- **Matrix cell states:** parity met, known gap, new gap, reference broken, report only
  (PS-013), not run, not applicable.

## Status

Every spec PS-001 to PS-013 has tests. All specs are still Draft: moving one to Approved is a
human review (and needs a pinned `source_sha`, which the Docker-guide specs lack). Specs run on
Docker or podman; PS-004 AC2 uses a compose provider (`docker compose`, or `podman-compose` from
the `podman` extra) and skips without one.

Not done yet:

- PS-006 (Compose dev workspace): needs the guide's Dockerfile from
  https://github.com/shakirth-anisha/docker-ros2-workspace and `oeros-container-devcontainer`,
  which is not in the current build list.
- PS-001 AC7 (`ROS_AUTOMATIC_DISCOVERY_RANGE`) has no test.
- PS-012 uses recorded YAML contracts instead of Goss.
- `--reuse-reference` (caching OSRF results by digest) is not implemented.
- The reporting extras in `parity.yml` (PR comments, GitHub Pages, gap issues) are TODOs.

Timing note: probes poll for readiness instead of sleeping, because cold container starts are
slow on spinning disks. A full run over all tiers takes well over half an hour there.
