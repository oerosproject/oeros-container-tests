---
id: PS-003
title: Talker and listener in one container
source: ros2_documentation/lyrical/source/Developer-Tools/Build/Run-2-nodes-in-single-or-separate-docker-containers.rst
source_sha: 3f6db02485e159bb6d5d5b680b6f5c3aa183c431  # ros2_documentation lyrical HEAD on 2026-09-27
tiers: [desktop, desktop-full]
status: Draft
---

Workflow: start the `demo_nodes_cpp` talker and listener in one container, as in the
"single container" half of the Run 2 nodes page.

AC1: the listener logs 3 or more `I heard` lines within 15 s of the talker's first message
AC2: the same holds with `demo_nodes_py` (rclpy talker and listener)

The 15 s budget counts from the talker's first message. Nodes get up to 120 s to start, because
cold container starts on slow storage dominate. Out of scope: interactive `-it` sessions.
