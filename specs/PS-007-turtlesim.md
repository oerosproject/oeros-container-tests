---
id: PS-007
title: Turtlesim nodes, topics, services, parameters, actions
source: ros2_documentation/lyrical/source/Get-Started/Introducing-Turtlesim/Introducing-Turtlesim.rst
source_sha: 3f6db02485e159bb6d5d5b680b6f5c3aa183c431  # ros2_documentation lyrical HEAD on 2026-09-27
tiers: [desktop, desktop-full]
status: Draft
---

Also draws on the nodes, topics, services, parameters and actions tutorials under
`ROS-Framework/` in the same tree.

Workflow: the First Steps tutorials against a headless turtlesim (Xvfb sidecar or the Qt
offscreen platform). `turtle_teleop_key` is interactive, so publishing to `/turtle1/cmd_vel`
stands in for it. The tutorials' `apt install` steps become "package is present"
(`ros2 pkg prefix turtlesim`).

AC1: `ros2 pkg prefix turtlesim` succeeds
AC2: `ros2 topic list` shows `/turtle1/cmd_vel`, `/turtle1/pose` and `/turtle1/color_sensor`
AC3: the `/turtle1/teleport_absolute` service (`turtlesim_msgs/srv/TeleportAbsolute`) moves the pose reported on `/turtle1/pose`
AC4: `ros2 param set /turtlesim background_r 255` takes effect (`param get` returns 255)
AC5: the `/turtle1/rotate_absolute` action goal (`turtlesim_msgs/action/RotateAbsolute`) succeeds

Turtlesim runs on Qt's `offscreen` platform here; PS-011 covers a real Xvfb display. In Lyrical the
service and action types live in `turtlesim_msgs`, not `turtlesim`.

Out of scope: the interactive teleop node, screenshots (PS-011).
