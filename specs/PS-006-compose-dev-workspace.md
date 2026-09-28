---
id: PS-006
title: Compose dev workspace
source: https://docs.docker.com/guides/ros2/
source_sha: null  # pin the source doc commit before moving to Approved
tiers: [ros-base, desktop]
status: Draft
---

Workflow: the Docker guide's development workspace builds with a swapped base image and works
as the non-root user. The OSRF side uses the guide's Dockerfile as written; the oeros side uses
`workspaces/docker-guide/Dockerfile.oeros`, which starts FROM `oeros-container-devcontainer`
with the same user and paths (see `specs/step-mapping.md`).

AC1: the guide's workspace image builds from the swapped base image
AC2: `echo $ROS_VERSION` prints `2` as the non-root user
AC3: `which colcon` succeeds as the non-root user

Out of scope: X11 forwarding (PS-011), `rosdep install` (report-only: `rosdep check`).
