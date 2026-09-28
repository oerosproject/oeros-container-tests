---
id: PS-008
title: rclpy publisher script
source: https://docs.docker.com/guides/ros2/
source_sha: null  # pin the source doc commit before moving to Approved
tiers: [desktop, desktop-full]
status: Draft
---

Workflow: the Docker guide's `move_turtle.py` rclpy script (kept verbatim in
`tests/fixtures/move_turtle.py`) publishes velocity commands to a
running turtlesim.

AC1: `move_turtle.py` runs to completion with exit code 0
AC2: the pose on `/turtle1/pose` changes while the script runs

Out of scope: writing the script interactively.
