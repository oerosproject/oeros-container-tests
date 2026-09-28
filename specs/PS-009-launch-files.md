---
id: PS-009
title: Launch files
source: ros2_documentation/lyrical/source/Developer-Tools/Launch/Creating-Launch-Files.rst
source_sha: 3f6db02485e159bb6d5d5b680b6f5c3aa183c431  # ros2_documentation lyrical HEAD on 2026-09-27
tiers: [desktop, desktop-full]
status: Draft
---

Workflow: the launch tutorial's two-turtlesim launch file.

AC1: `ros2 launch` of a two-turtlesim launch file starts both nodes (two `process started` lines)
AC2: `ros2 node list` shows both turtlesim nodes
AC3: `launch_test` runs a small launch_testing test that launches the C++ talker and checks its
output (proves launch_testing works in the image; `launch_pytest` is not shipped by either family)

Out of scope: the `mimic` node and remapping variants.
