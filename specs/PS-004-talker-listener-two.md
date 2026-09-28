---
id: PS-004
title: Talker and listener in two containers
source: ros2_documentation/lyrical/source/Developer-Tools/Build/Run-2-nodes-in-single-or-separate-docker-containers.rst
source_sha: 3f6db02485e159bb6d5d5b680b6f5c3aa183c431  # ros2_documentation lyrical HEAD on 2026-09-27
tiers: [desktop, desktop-full]
status: Draft
---

Workflow: run the talker and the listener in separate containers on one network, first with
`docker run` and then with the compose file. Cross-family pairs use `compose/interop.yaml`
with `RMW_IMPLEMENTATION` pinned explicitly, because the two families may default to different
middleware (PS-001 records each default).

Each test gets its own compose network and a unique `ROS_DOMAIN_ID`.

AC1: with `docker run` on a shared network, the listener receives 3 or more messages within 15 s
AC2: with `compose/talker-listener.yaml`, the listener receives 3 or more messages within 15 s
AC3: an oeros talker and an OSRF listener work together (compose/interop.yaml)
AC4: an OSRF talker and an oeros listener work together (compose/interop.yaml)

Out of scope: interactive `-it` sessions, multi-host networks.
