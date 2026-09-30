# Manual test guides

Step-by-step instructions for running by hand what the automated suite runs. Each guide is one
parity spec (`specs/PS-*.md`) and every step is tagged with the acceptance criterion it checks
(`AC1`, `AC2`, ...), which is the same ID the pytest tests carry in `@pytest.mark.spec`.

| Guide | Kind |
| --- | --- |
| PS-001 environment, PS-002 introspection, PS-005 package build, PS-013 inventory | **Generated** from the commands the tests run (`python -m tools.gen_manual`). Do not edit. |
| PS-003, 004, 007, 008, 009, 010, 011, 012 | **Hand-written**. The tests run one long shell script or manage several containers, which does not read as steps. `spec-lint` fails if a guide leaves out a criterion of its spec. |
| PS-006 | No guide yet: the spec has no tests. |

## Setup

Run each guide twice, once per image family, and compare. The pairs come from
[`images.yaml`](../../images.yaml); the oeros column is the amd64 name (see below for arm64):

| Tier | OSRF image | oeros image (amd64) |
| --- | --- | --- |
| `ros-core` | `docker.io/library/ros:lyrical-ros-core` | `ghcr.io/oerosproject/oeros-x86-64-ros-core:latest` |
| `ros-base` | `docker.io/library/ros:lyrical-ros-base` | `ghcr.io/oerosproject/oeros-x86-64-ros-base:latest` |
| `perception` | `docker.io/library/ros:lyrical-perception` | `ghcr.io/oerosproject/oeros-x86-64-perception:latest` |
| `simulation` | `docker.io/osrf/ros:lyrical-simulation` | `ghcr.io/oerosproject/oeros-x86-64-simulation:latest` |
| `desktop` | `docker.io/library/ros:lyrical-desktop` | `ghcr.io/oerosproject/oeros-x86-64-desktop:latest` |
| `desktop-full` | `docker.io/osrf/ros:lyrical-desktop-full` | `ghcr.io/oerosproject/oeros-x86-64-desktop-full:latest` |

`images.yaml` is the source of truth (the suite also pins the OSRF images by digest); check it
if this table looks out of date. The oeros repository name bakes in the architecture:
`oeros-x86-64-<tier>` for amd64, `oeros-arm64-<tier>` for arm64 (the tag is always `latest`,
never a per-build tag). Locally built oeros images instead use the recipe name and are tagged
`oeros-container-<tier>:latest-<arch>` after `python -m tools.load_oeros`.

```sh
export OSRF_IMAGE=docker.io/library/ros:lyrical-desktop
export OEROS_IMAGE=ghcr.io/oerosproject/oeros-x86-64-desktop:latest   # oeros-arm64-desktop on arm64
IMAGE=$OSRF_IMAGE    # then repeat the guide with IMAGE=$OEROS_IMAGE
```

With rootless podman, use `podman` for `docker` (and `podman-compose` for `docker compose`).

## Things that differ between the families

- **Entrypoint.** OSRF images run `/ros_entrypoint.sh`, which sources the ROS setup. The oeros
  images have no entrypoint, so a plain `run` has no ROS environment (this is the PS-001 gap).
  The guides therefore source `/opt/ros/lyrical/setup.sh` explicitly wherever a spec is not
  about the entrypoint, as the tests do.
- **Shell.** The oeros images are busybox-based. `timeout` does not exist and `head -n 3` works
  where `head -3` does not. `/bin/sh` is bash there and dash in the OSRF images.
- **`docker exec` skips the entrypoint**, so exec'd commands always need the setup sourced.
  The guides define a small helper for that:

  ```sh
  rosx() { docker exec "$CONTAINER" sh -c ". /opt/ros/lyrical/setup.sh && $*"; }
  ```

## Clean up

Every guide that starts containers ends with the commands to remove them. If a step fails
half-way, `docker rm -f <names>` and `docker network rm ros-net` put you back at the start.

## Regenerating the generated guides

```sh
pytest --record-commands --run-id manual-rec --spec PS-001 --spec PS-002 --spec PS-005 \
       --spec PS-013 --tier ros-base --tier dev
python -m tools.gen_manual --from results/manual-rec/commands.json
python -m tools.gen_manual --check     # spec-lint runs this too; needs no containers
```
