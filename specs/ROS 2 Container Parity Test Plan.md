# ROS 2 Container Parity Test Plan

Sep 27, 2026 · @Rob

## Purpose and goals

This plan builds a spec-driven test suite that proves the meta-oeros container images (ROS 2 Lyrical on Yocto Wrynose) match the official OSRF / Docker Hub images for every workflow in the Docker ROS 2 guide and the ROS 2 docs pages listed below. Every test runs against both image families, and the result is a per-tier parity matrix, not just pass/fail.

**Goals**

- Each workflow in the source docs is captured as a numbered parity spec with testable acceptance criteria.
- The same test runs against the OSRF reference image and the oeros candidate image for the matching REP-2001 tier.
- Differences are reported as named gaps (missing packages, executables, interfaces, env vars) that feed back into meta-oeros work.
- One command runs the suite locally; the same entry point runs in GitHub Actions on x86-64 and arm64.

**Non-goals**

- Byte-level or package-name equality with Ubuntu. Parity means equivalent capability, not the same `apt` names.
- Image size and build performance; the build report already covers those.
- Testing `apt`, `sudo` or `rosdep` install flows literally, since the oeros images have no apt and no sudo. These steps are mapped to equivalents (see Image matrix).
- Running under podman in the first release. Docker is the only runtime in the initial matrix; podman is a later addition (see Decisions).
- Differential parity for leaf images (tools, ci, rviz, turtlebot3, foxglove-bridge). They join later with contract and smoke checks only.

**Source documents**

- [Docker guide: Introduction to ROS 2 Development with Docker](https://docs.docker.com/guides/ros2/)
- [Running ROS 2 nodes in Docker](https://github.com/ros2/ros2_documentation/blob/lyrical/source/Developer-Tools/Build/Run-2-nodes-in-single-or-separate-docker-containers.rst)
- [Setting up your environment](https://github.com/ros2/ros2_documentation/blob/lyrical/source/Get-Started/Configuring-ROS2-Environment.rst)
- [Developing a ROS 2 package](https://github.com/ros2/ros2_documentation/blob/lyrical/source/Developer-Tools/Build/Developing-a-ROS-2-Package.rst)
- [First steps with ROS](https://github.com/ros2/ros2_documentation/blob/lyrical/source/First-Steps.rst) and the turtlesim tutorials it links to
- [OEROS Container Build Report](https://claude.ai/artifact/1t6EFBZPx41FLdjHNhemtj) for the oeros image catalog

## Spec-driven development model

Every test traces back to a numbered acceptance criterion, and no test is trusted until it passes on the OSRF reference image. That rule keeps the suite honest: a failure on oeros then means a real gap, not a broken test.

&#91;embedded content: parity spec lifecycle · 6 steps, 2 decisions\]

A failure on oeros becomes a strict `xfail` linked to a meta-oeros issue. When the fix lands, the test XPASSes, the strict marker turns that into a failure, and the spec has to be updated to close the gap.

**Spec artifacts**

| Artifact | Lives in | Purpose |
| --- | --- | --- |
| Spec 0020: Container parity test suite | oerosproject `specs/` | Umbrella spec using `SPEC_TEMPLATE.md`; links Specs 0001, 0002, 0008, 0014 |
| Test plan for 0020 | oerosproject, from `TEST_PLAN_TEMPLATE.md` | CI matrix: distro × image tier × arch × image family |
| ADR 0004: Parity test tooling | oerosproject `adrs/` | Records the pytest + testcontainers + compose choice and the rejected options |
| Parity specs PS-001 … PS-0NN | Test repo `specs/` | One per documented workflow, each with numbered acceptance criteria |
| Step-mapping table | Test repo `specs/step-mapping.md` | How each apt, sudo or rosdep step maps onto oeros images |

**Status lifecycle for a parity spec:** Draft → Approved (merged) → Implemented (tests pass on OSRF) → Verified (tests pass on oeros) or Gap (strict xfail with an open issue).

**Traceability.** Each test carries `@pytest.mark.spec("PS-003", "AC2")`. A conftest hook writes a traceability file, and a `spec-lint` job fails the build when an approved criterion has no test or a test names an unknown criterion.

**Parity spec template** (Markdown with YAML front matter, so tooling can read it):

```markdown
---
id: PS-003
title: Talker/listener across two containers
source: ros2_documentation/.../Run-2-nodes-in-single-or-separate-docker-containers.rst
tiers: [desktop]
status: Approved
---
AC1: listener receives >= 3 "Hello World" messages within 15 s
AC2: works with an oeros talker and an OSRF listener, and the reverse
Out of scope: interactive -it sessions
```

## Spec catalog

Thirteen parity specs cover the five source documents. PS-001, PS-002, PS-012 and PS-013 run on every tier; the rest run on the tiers that ship the packages they need.

| Spec | Workflow | Source | Tiers | Key acceptance criteria |
| --- | --- | --- | --- | --- |
| PS-001 | Environment setup | Configuring env; Docker guide | all | `ROS_DISTRO=lyrical`, `ROS_VERSION=2`, `ROS_PYTHON_VERSION=3`; `/opt/ros/lyrical/setup.bash` sources cleanly in bash and sh; `ros2 --help` exits 0; the entrypoint sources the setup; `ROS_DOMAIN_ID` and `ROS_AUTOMATIC_DISCOVERY_RANGE` are honored |
| PS-002 | CLI introspection | Run 2 nodes | all | `ros2 pkg list`, `ros2 pkg executables` and `ros2 interface list` succeed; the result sets are captured for PS-013 |
| PS-003 | Talker and listener in one container | Run 2 nodes | desktop, desktop-full | listener logs 3 or more `I heard` lines within 15 s |
| PS-004 | Talker and listener in two containers | Run 2 nodes | desktop, desktop-full | works with `docker run` and with the compose file; works with an oeros talker and an OSRF listener, and the reverse |
| PS-005 | Create and build a package | Developing a package | OSRF ros-base; oeros ros-dev | `ros2 pkg create` for ament\_cmake and ament\_python; `colcon build` succeeds; the built executables run from the overlay |
| PS-006 | Compose dev workspace | Docker guide | ros-base, desktop | the guide's workspace builds with a swapped base image; `echo $ROS_VERSION` and `which colcon` succeed as the non-root user |
| PS-007 | Turtlesim nodes, topics, services, parameters, actions | First Steps tutorials; Docker guide | desktop, desktop-full | expected topics listed; `teleport_absolute` moves the pose; `param set background_r` takes effect; `rotate_absolute` action succeeds |
| PS-008 | rclpy publisher script | Docker guide | desktop, desktop-full | `move_turtle.py` runs and `/turtle1/pose` changes |
| PS-009 | Launch files | First Steps (launch tutorial) | desktop, desktop-full | a two-turtlesim launch file starts both nodes; `ros2 node list` shows both |
| PS-010 | Record and play back | First Steps (rosbag2 tutorial) | ros-base and up | `ros2 bag record` writes a bag; `ros2 bag info` reports the message count; `ros2 bag play` republishes it |
| PS-011 | GUI tools, headless | Docker guide; First Steps (rqt\_console) | desktop, desktop-full | turtlesim, `rqt_gui` and `rqt_console` start under Xvfb; a screenshot of the display is not blank |
| PS-012 | Static image contract | All | all | entrypoint, default shell, env, workdir and user match the recorded contract (Goss) |
| PS-013 | Package inventory parity | All | all | the difference in packages, executables and interfaces between the two families is reported per tier; report-only until the baseline is agreed |

The interactive keyboard step (`turtle_teleop_key`) is replaced by publishing to `/turtle1/cmd_vel`. The Docker guide's `apt install` steps become "package is present in the matching tier" (see Image matrix).

## Image matrix

Six REP-2001 tiers are paired one-to-one, for ROS 2 Lyrical on x86-64 and arm64. The OSRF names are the ones the build report compared against; the oeros names come from the meta-oeros `feature/ros2-container-images` branch.

| Tier | OSRF reference | oeros candidate |
| --- | --- | --- |
| ros-core | `ros:lyrical-ros-core` | `oeros-container-ros-core` |
| ros-base | `ros:lyrical-ros-base` | `oeros-container-ros-base` |
| perception | `ros:lyrical-perception` | `oeros-container-perception` |
| simulation | `osrf/ros:lyrical-simulation` | `oeros-container-simulation` |
| desktop | `osrf/ros:lyrical-desktop` | `oeros-container-desktop` |
| desktop-full | `osrf/ros:lyrical-desktop-full` | `oeros-container-desktop-full` |
| dev (build tools) | `ros:lyrical-ros-base` | `oeros-container-ros-dev`, `oeros-container-devcontainer` |

The last row exists because OSRF ros-base ships colcon and rosdep, while oeros keeps build tools in ros-dev. This split is an accepted, intended difference. PS-005 and PS-006 compare against that pairing, and PS-013 reports the split as known, not as a gap.

oeros images are published to GHCR as `ghcr.io/oerosproject/oeros-<arch>-<tier>:latest`, for example `oeros-x86-64-ros-core` (amd64) and `oeros-arm64-ros-core` (arm64) — the architecture is baked into the repository name rather than the tag, and the tag is always `latest` (see the Decisions entry below and `images.yaml`). Leaf images (tools, ci, rviz, turtlebot3, foxglove-bridge) are not in this matrix yet; see Decisions.

The matrix lives in one file, `images.yaml`, keyed by tier and family. Tests never hard-code image names. Image references are pinned by digest in CI so a moving OSRF tag cannot change results silently, and a weekly job refreshes the pins.

**Mapping steps that only exist on Ubuntu**

| Doc step | OSRF image | oeros image |
| --- | --- | --- |
| `sudo apt install ros-lyrical-turtlesim` (and rqt, rviz2, demo nodes) | run as written in an "install" variant; the desktop tier already has them | assert the package is present: `ros2 pkg prefix <pkg>` |
| `sudo` | root by default; not needed | not used; tests run as the image's default user |
| Docker guide `Dockerfile` (apt, `useradd`) | used as written | `Dockerfile.oeros` variant FROM `oeros-container-devcontainer`, same user and paths |
| `rosdep install` | run | report-only: `rosdep check`, since packages are baked in at build time |
| `xhost +local:docker` and X11 forwarding | Xvfb sidecar sharing `/tmp/.X11-unix` | same Xvfb sidecar, so both families see the same display |
| `docker run -it` | `docker run --rm` with a timeout | same |

## Test architecture and tooling

pytest is the single entry point: it reads the specs and the image matrix, runs every probe against both families, and writes all results. Everything else is a driver it calls.

&#91;embedded content: test architecture · inputs, runner, drivers, images, results\]

The differential probe is the core idea: run the same command in the OSRF and oeros images for a tier, then compare the outputs as sets rather than as text. Commands run through each image's own entrypoint, never a hard-coded shell, because the oeros base is busybox; PS-012 records which shell each image provides.

| Tool | Role | Used by |
| --- | --- | --- |
| pytest | Runner, parametrization over the image matrix, markers (`gui`, `multi_container`, `build`, `slow`), JUnit output | all |
| testcontainers-python | Start, exec and tear down single containers from fixtures; fall back to the `docker` SDK where needed | PS-001 to PS-003, PS-005, PS-007 to PS-010 |
| Docker Compose | Multi-container scenarios, started from fixtures with `docker compose up --wait` and healthchecks | PS-004, PS-006, PS-011 |
| launch\_testing / launch\_pytest | Assertions on node output inside the container; also proves launch\_testing works in oeros | PS-003, PS-009 |
| Goss (dgoss) | Fast YAML checks of files, env, user and entrypoint | PS-012 |
| Xvfb sidecar | Shared virtual display for GUI tools, with a screenshot check | PS-011 |
| syft | SBOM per image, diffed across families | PS-013 |
| syrupy | Snapshots of probe output to catch drift between runs | PS-002, PS-013 |
| nox | Named local sessions that call the same pytest command CI uses | local runs |

**Considered and not chosen as the core** (recorded in ADR 0004): prysk transcripts read like the tutorials but lack fixtures and parametrization; BATS is simpler but weak at multi-container setup; Dagger adds a second pipeline language; Robot Framework gives nice reports but is heavier than needed. prysk stays an option later for generating doc-transcript tests from the RST sources.

## Repository layout

The suite lives in its own repository, proposed as `oeros-container-tests`, so it can test any published image without a Yocto checkout. meta-oeros CI calls it as a reusable workflow.

```text
oeros-container-tests/
├── specs/
│   ├── PS-001-environment.md … PS-013-inventory.md
│   └── step-mapping.md
├── images.yaml                 # tier × family × arch → image ref (+ digest)
├── contracts/                  # PS-012 Goss files, one per family
│   ├── osrf.goss.yaml
│   └── oeros.goss.yaml
├── compose/
│   ├── talker-listener.yaml    # PS-004, image refs from env vars
│   ├── interop.yaml            # oeros ↔ OSRF pairs
│   └── xvfb.yaml               # PS-011 display sidecar
├── workspaces/
│   ├── docker-guide/           # PS-006: Dockerfile + Dockerfile.oeros
│   └── pkg-create/             # PS-005 fixtures
├── tests/
│   ├── conftest.py             # matrix fixtures, spec marker, parity collector
│   ├── plugins/spec_trace.py   # traceability.json + spec-lint
│   └── test_ps001_env.py … test_ps013_inventory.py
├── tools/
│   ├── spec_lint.py
│   └── parity_report.py        # parity.json → Markdown + HTML matrix
├── noxfile.py
├── pyproject.toml              # pinned test dependencies
└── .github/workflows/
    ├── parity.yml              # reusable (workflow_call) + PR trigger
    └── refresh-digests.yml     # weekly OSRF digest update PR
```

## Local execution

One `nox` command runs a named slice of the suite on a developer machine, using exactly the pytest invocation CI uses. Results land in `results/<run-id>/` in the same formats as CI.

**Prerequisites:** Docker Engine with Compose v2, Python 3.11 or newer, and nox (installed with `uv tool install nox` or pip). For arm64 on an x86-64 host, register QEMU binfmt handlers once with `docker run --privileged --rm tonistiigi/binfmt --install arm64`.

**Getting the oeros images.** There are two supported sources, chosen in `images.yaml` or overridden by environment variable:

1. **Local build:** load the OCI output from the bitbake deploy directory with the meta-oeros load/push helper (`scripts/`, added in commit `1d0a5c6`), then set `OEROS_SOURCE=local`.
2. **Registry:** set `OEROS_REGISTRY=<registry>/<namespace>` to pull published images. The default is GHCR (`ghcr.io/oerosproject`); the repository name is per architecture (`oeros-x86-64-<tier>` or `oeros-arm64-<tier>`) and always tagged `latest` — see the Decisions entry above.

OSRF images are always pulled from Docker Hub by pinned digest.

**Sessions**

| Session | What it runs | Typical time |
| --- | --- | --- |
| `nox -s smoke` | PS-001, PS-002, PS-012 on ros-core and ros-base, host architecture | minutes |
| `nox -s parity -- --tier desktop` | every spec for one tier, both families | longer; desktop images are about 1.5 GB each |
| `nox -s gui` | PS-011 with the Xvfb sidecar | minutes |
| `nox -s arm64 -- --tier ros-base` | the same specs under QEMU emulation | slow; for spot checks only |
| `nox -s report` | builds the parity matrix from the last run | seconds |
| `nox -s lint` | spec-lint, ruff, Goss file validation | seconds |

For one spec, pass pytest options through: `nox -s parity -- --spec PS-004 -x`.

**Reusing the reference run.** OSRF results are cached by image digest, so an unchanged OSRF image is not retested on every local run. `--reuse-reference` uses the cache; CI always runs both families fresh.

The typical inner loop for a meta-oeros change is: rebuild the image with bitbake, load it, run `nox -s parity -- --tier <tier> --family oeros --reuse-reference`, then read the parity report.

## GitHub Actions

One workflow, `parity.yml`, runs the same `nox -s ci` entry point as local runs, with one job per tier and architecture. Each job tests both families on the same runner, so reference and candidate always see identical hardware.

&#91;embedded content: parity.yml pipeline · 4 triggers, 4 jobs, 3 outputs\]

This fits Spec 0014's rule that heavy builds stay on GitLab: bitbake still builds and pushes the oeros images on GitLab, and GitHub Actions only pulls and tests them. After a successful push, GitLab sends a `repository_dispatch` event carrying the new image digests.

**Triggers**

| Trigger | Scope | Gate |
| --- | --- | --- |
| `pull_request` | lint, plus smoke tiers (ros-core, ros-base) on x86-64, plus the full tier of any spec the PR changes | blocks merge |
| `push` to main | all tiers, x86-64 | updates the published report |
| `schedule` (nightly) | all tiers × both arches | opens or updates a gap issue per new failure |
| `repository_dispatch` / `workflow_dispatch` | tiers and digests given in the event or form | reports back to the caller |
| `workflow_call` | same as dispatch, for meta-oeros workflows | caller decides |

**Jobs**

1. **lint:** `spec-lint`, ruff, and Goss file validation on `ubuntu-latest`.
2. **resolve:** reads `images.yaml`, applies any digests from the event, and outputs the tier × arch matrix as JSON.
3. **parity:** `strategy.matrix` from resolve, with `fail-fast: false`.
   - `runs-on` is `ubuntu-24.04` for x86-64 and `ubuntu-24.04-arm` for arm64, so arm64 runs natively, not under QEMU.
   - Desktop tiers first free runner disk; each pair of desktop-full images is about 13 GB unpacked.
   - Logs in to Docker Hub with a read-only token to avoid anonymous pull limits.
   - Uploads `results/` as an artifact named `results-<tier>-<arch>`.
4. **report:** runs with `if: always()`, merges the artifacts, publishes JUnit as check runs, writes the parity matrix to the job summary, comments the parity change on PRs, and on main deploys Allure to GitHub Pages.

**Pass rules.** A job fails on any unexpected failure, any strict XPASS, or any OSRF failure (a broken reference means a broken test). Known gaps are strict xfails, so they stay visible in the report without turning PRs red.

**Runner sizing.** The standard hosted runners are enough for ros-core through perception. If the desktop tiers run out of disk or time, move only those cells to larger runners or to the AWS runners from ADR 0002 via a self-hosted label, with no change to the workflow logic.

## Results and reporting

Every run, local or CI, writes the same five outputs to `results/<run-id>/`, and `tools/parity_report.py` turns them into one parity matrix: specs as rows, tiers as columns.

| Output | Format | Consumer |
| --- | --- | --- |
| `junit.xml` | JUnit XML, one test case per spec criterion × family | GitHub check runs, any CI |
| `allure-results/` | Allure raw results with logs, compose output and screenshots attached | Allure HTML on GitHub Pages |
| `parity.json` | per tier: spec, criterion, OSRF result, oeros result, set differences | the matrix and PR comments |
| `traceability.json` | criterion → tests → results | spec-lint and spec status updates |
| `sbom/` | syft SBOMs per image | PS-013 package difference |

**Cell states in the matrix:** parity met, known gap (strict xfail, linked issue), new gap (unexpected oeros failure), reference broken (OSRF failed, so the test is suspect), and not applicable (the tier lacks the package by design).

**Where it shows up**

- **Job summary:** the matrix as Markdown on every run.
- **Pull requests:** one comment, updated in place, listing only cells that changed against main.
- **GitHub Pages:** the Allure report and matrix history from main and nightly runs.
- **Issues:** the nightly job opens one issue per new gap, labelled with spec and tier, and closes it when the cell reaches parity.

Spec status follows the results: when every criterion in a spec is "parity met" on all its tiers, `spec-lint` proposes moving it to Verified.

## Milestones

The work runs in five phases, and each ends at a gate that the spec-driven loop can check. Specs come first so every later phase has approved criteria to test against.

&#91;embedded content: milestones · 5 phases, 5 gates, not to scale\]

No dates are set yet. Phases 0 and 1 are small; Phase 2 is the bulk of the test writing, and Phase 3 can start in parallel once the smoke specs pass.

Two follow-ups sit after Phase 3 and are not scheduled: adding the leaf images with contract and smoke checks once every spec is Verified or Gap on all six tiers, and adding a podman nightly job.

## Risks and open questions

The biggest risk is middleware mismatch: if the two families default to different RMW implementations, cross-family tests fail for reasons unrelated to parity.

| Risk | Mitigation |
| --- | --- |
| Different default RMW between families | PS-001 records each image's default; interop tests (PS-004) pin `RMW_IMPLEMENTATION` explicitly |
| DDS discovery on Docker bridge networks in CI | Each test gets its own compose network and a unique `ROS_DOMAIN_ID`; fallback to static peers if multicast is blocked |
| arm64 availability of `osrf/ros` desktop tags | Verify in Phase 1; if missing, arm64 desktop cells compare against the x86-64 reference sets |
| Runner disk and time for desktop-full | Free disk step; move only those cells to larger or self-hosted runners |
| Docker Hub pull limits | Authenticated pulls with a read-only token; pull by digest once per job |
| Timing flakiness in multi-node tests | Generous timeouts; at most one rerun, only for the `multi_container` marker, and reruns are reported |
| Upstream docs change under the specs | Each spec pins the source doc's commit SHA in its front matter; a monthly job flags changed sources |
| Deployed OCI artifacts vanishing from the build host (noted in the build report) | Prefer the registry source in CI (GHCR); local runs check digests before testing |
| Podman behaves differently from Docker (socket, networking, multicast) when it is added later | Keep runtime calls behind one fixture now; add podman as a nightly, x86-64 only job before making it a gate |
| GHCR registry choice conflicts with the outcome of RFC 0001 | Registry is set only through `OEROS_REGISTRY` and `images.yaml`, so a change touches config, not tests |

**Decisions**

These were the open questions in the first draft. All five are now decided.

- [x] **Registry and tag scheme:** GHCR. Superseded 2026-09-30 by the actual naming meta-oeros CI uses (`yocto-containers/oci-image-naming-rules.md`): images are published per architecture as `ghcr.io/oerosproject/oeros-x86-64-<tier>:latest` or `oeros-arm64-<tier>:latest` — the build's multiconfig name plus the recipe suffix, always tagged `latest` (the OCI layout carries no other tag to preserve). The original plan here (`oeros-container-<tier>:lyrical-<yocto-release>` plus an immutable git-sha tag) was never built; there is no digest or immutable-tag pin for oeros images, only for the OSRF reference. This still needs to be reconciled with RFC 0001 on binary artifact hosting.
- [x] **Repository home:** standalone `oeros-container-tests` repository. meta-oeros CI calls it as a reusable workflow.
- [x] **ros-base vs ros-dev build-tools split:** accepted as an intended difference. PS-005 and PS-006 keep the ros-dev / devcontainer pairing, and PS-013 reports the split as known, not as a gap.
- [x] **Podman:** Docker first, podman later. Runtime-specific calls stay behind a small fixture so a podman nightly job can be added without changing the specs. Podman is not part of the initial matrix.
- [x] **Leaf images (tools, ci, rviz, turtlebot3, foxglove-bridge):** they join after the six tiers are stable, meaning every spec is Verified or Gap on all tiers (after Phase 3). Most have no OSRF equivalent, so they get contract and smoke checks only, not differential parity.

## Sources

- [Docker guide: Introduction to ROS 2 Development with Docker](https://docs.docker.com/guides/ros2/)
- [Running ROS 2 nodes in Docker](https://github.com/ros2/ros2_documentation/blob/lyrical/source/Developer-Tools/Build/Run-2-nodes-in-single-or-separate-docker-containers.rst)
- [Setting up your environment](https://github.com/ros2/ros2_documentation/blob/lyrical/source/Get-Started/Configuring-ROS2-Environment.rst)
- [Developing a ROS 2 package](https://github.com/ros2/ros2_documentation/blob/lyrical/source/Developer-Tools/Build/Developing-a-ROS-2-Package.rst)
- [First steps with ROS](https://github.com/ros2/ros2_documentation/blob/lyrical/source/First-Steps.rst)
- [OEROS Container Build Report](https://claude.ai/artifact/1t6EFBZPx41FLdjHNhemtj)
- [oerosproject: spec template, Specs 0002, 0008, 0014 and ADR 0002](https://github.com/robwoolley/oerosproject)
- [GitHub Changelog: arm64 hosted runners for public repositories are generally available](https://github.blog/changelog/2025-08-07-arm64-hosted-runners-for-public-repositories-are-now-generally-available/)
- [GitHub Changelog: arm64 standard runners in private repositories](https://github.blog/changelog/2026-01-29-arm64-standard-runners-are-now-available-in-private-repositories/)
