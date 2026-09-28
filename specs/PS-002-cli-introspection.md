---
id: PS-002
title: CLI introspection
source: ros2_documentation/lyrical/source/Developer-Tools/Build/Run-2-nodes-in-single-or-separate-docker-containers.rst
source_sha: 3f6db02485e159bb6d5d5b680b6f5c3aa183c431  # ros2_documentation lyrical HEAD on 2026-09-27
tiers: [all]
status: Draft
---

Workflow: a user explores an image with `ros2 pkg`, `ros2 interface` and friends.

Probes source `/opt/ros/lyrical/setup.sh` explicitly, so this spec measures the CLI and does
not depend on the entrypoint (PS-001 covers that). Only portable shell is used in the image,
because the oeros base has busybox utilities.

AC1: `ros2 pkg list` exits 0 and lists `rclcpp`, `rclpy` and `std_msgs`
AC2: `ros2 pkg executables` exits 0 and prints at least one `<package> <executable>` line
AC3: `ros2 interface list` exits 0 and lists `std_msgs/msg/String`
AC4: the package, executable and interface sets are captured as artifacts for PS-013

Out of scope: comparing the sets between families (PS-013).
