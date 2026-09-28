---
id: PS-005
title: Create and build a package
source: ros2_documentation/lyrical/source/Developer-Tools/Build/Developing-a-ROS-2-Package.rst
source_sha: 3f6db02485e159bb6d5d5b680b6f5c3aa183c431  # ros2_documentation lyrical HEAD on 2026-09-27
tiers: [dev]
status: Draft
---

Workflow: create an `ament_cmake` and an `ament_python` package with `ros2 pkg create`, build
them with `colcon build`, source the overlay and run the executables.

The `dev` tier pairs OSRF `ros:lyrical-ros-base` (which ships colcon and a compiler) with the
oeros build-tools image `oeros-container-ros-dev`. That split is an accepted difference
(see the plan's Decisions), so this spec compares against the pairing and not against oeros
ros-base.

The probe runs as the image's default user in `/tmp/ws`, with the ROS setup sourced explicitly.

AC1: `ros2 pkg create --build-type ament_cmake --node-name my_node my_cmake_pkg` exits 0
AC2: `ros2 pkg create --build-type ament_python --node-name my_py_node my_py_pkg` exits 0
AC3: `colcon build` of the workspace exits 0
AC4: after sourcing the overlay, `ros2 run` starts both executables and they print their greeting

Out of scope: `rosdep install`, testing the packages (`colcon test`), symlink installs.
