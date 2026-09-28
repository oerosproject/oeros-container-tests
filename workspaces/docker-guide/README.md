# PS-006 workspace: Docker guide dev environment

This directory holds the fixtures for PS-006 (Compose dev workspace):

- `Dockerfile`: the workspace Dockerfile (`ws_linux/`) from the guide's sample repository
  https://github.com/shakirth-anisha/docker-ros2-workspace, copied verbatim with a pinned commit, with the base image as `ARG BASE_IMAGE` (used as written for the OSRF family).
- `Dockerfile.oeros`: the oeros variant, FROM `oeros-container-devcontainer`, same user and
  paths, with the apt and `useradd` steps replaced as in `specs/step-mapping.md`.

Neither file exists yet: PS-006 is Draft, and `oeros-container-devcontainer` is not in the
current build list (`oci-image-paths.md`). Add them together with the PS-006 tests.
