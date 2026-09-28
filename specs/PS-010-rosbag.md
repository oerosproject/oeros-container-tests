---
id: PS-010
title: Record and play back
source: ros2_documentation/lyrical/source/ROS-Framework/interfaces/Working-with-interfaces/Recording-And-Playing-Back-Data/Recording-And-Playing-Back-Data.rst
source_sha: 3f6db02485e159bb6d5d5b680b6f5c3aa183c431  # ros2_documentation lyrical HEAD on 2026-09-27
tiers: [ros-base, perception, simulation, desktop, desktop-full]
status: Draft
---

Workflow: record a topic with `ros2 bag record`, inspect the bag with `ros2 bag info`, and
republish it with `ros2 bag play`, as in the rosbag2 tutorial.

The tutorial records turtlesim's `/turtle1/cmd_vel`. Turtlesim is only in the desktop tiers, so
the probe records a `std_msgs/msg/String` topic published by `ros2 topic pub` inside the same
container, which runs on every tier that ships rosbag2. In Lyrical the topics go behind
`--topics`, and there is no terminal, so `--disable-keyboard-controls` is needed and the
recorder is stopped with SIGTERM.

AC1: `ros2 bag record` writes a bag directory with `metadata.yaml` and a storage file
AC2: `ros2 bag info` exits 0 and reports at least 10 messages on the recorded topic
AC3: `ros2 bag play` republishes the recorded messages so a subscriber receives them

Out of scope: turtlesim's `cmd_vel` topic, compression and storage presets, split bags.
