---
id: PS-011
title: GUI tools, headless
source: https://docs.docker.com/guides/ros2/ and ros2_documentation/lyrical/source/ROS-Framework/nodes/Working-with-nodes/Using-Rqt-Console/Using-Rqt-Console.rst
source_sha: null  # pin the source doc commit before moving to Approved
tiers: [desktop, desktop-full]
status: Draft
---

Workflow: GUI tools run against a shared Xvfb display instead of X11 forwarding
(`xhost +local:docker`). The Xvfb sidecar from `compose/xvfb.yaml` shares `/tmp/.X11-unix`,
so both families see the same display.

AC1: `turtlesim_node` starts under Xvfb and stays up for 10 s
AC2: `rqt_gui` starts under Xvfb and stays up for 10 s
AC3: `rqt_console` starts under Xvfb and stays up for 10 s
AC4: a screenshot of the display with turtlesim running is not blank

Out of scope: rviz2, input events, GPU acceleration.
