---
id: PS-001
title: Environment setup
source: ros2_documentation/lyrical/source/Get-Started/Configuring-ROS2-Environment.rst
source_sha: 3f6db02485e159bb6d5d5b680b6f5c3aa183c431  # ros2_documentation lyrical HEAD on 2026-09-27
tiers: [all]
status: Draft
---

Workflow: a user starts the image and gets a working ROS 2 environment, as described in
"Setting up your environment" and the Docker guide.

Probes run through each image's own entrypoint. `setup.bash` is checked in bash and `setup.sh`
in sh, bypassing the entrypoint to get a clean shell; a missing bash is reported as a gap, not
skipped. The OSRF images set only `ROS_DISTRO` in the image config and rely on their entrypoint
(`/ros_entrypoint.sh`) for everything else, so AC1, AC4 and AC5 are what show whether an image
sets up the environment for a plain `run`.

AC1: `ROS_DISTRO=lyrical`, `ROS_VERSION=2` and `ROS_PYTHON_VERSION=3` are set in the default environment
AC2: `/opt/ros/lyrical/setup.bash` sources cleanly in bash
AC3: `/opt/ros/lyrical/setup.sh` sources cleanly in sh
AC4: `ros2 --help` exits 0 through the entrypoint
AC5: the entrypoint sources the setup, so `ros2` resolves under `/opt/ros/lyrical` without a manual source
AC6: `ROS_DOMAIN_ID` is honored (rclpy reports the domain it was given)
AC7: `ROS_AUTOMATIC_DISCOVERY_RANGE` is honored (test pending; needs a probe that reads it back)
AC8: the default RMW implementation is recorded as an artifact (`ros2 doctor --report`), so cross-family specs know what to pin

Out of scope: interactive `-it` sessions, `.bashrc` edits.
