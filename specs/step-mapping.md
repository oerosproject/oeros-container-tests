# Step mapping: doc steps that only exist on Ubuntu

The oeros images have no apt and no sudo. This table says how each documented step is tested
against both families (from the plan's "Mapping steps that only exist on Ubuntu").

| Doc step | OSRF image | oeros image |
| --- | --- | --- |
| `sudo apt install ros-lyrical-turtlesim` (and rqt, rviz2, demo nodes) | run as written in an "install" variant; the desktop tier already has them | assert the package is present: `ros2 pkg prefix <pkg>` |
| `sudo` | root by default; not needed | not used; tests run as the image's default user |
| Docker guide `Dockerfile` (apt, `useradd`) | used as written | `Dockerfile.oeros` variant FROM `oeros-container-devcontainer`, same user and paths |
| `rosdep install` | run | report-only: `rosdep check`, since packages are baked in at build time |
| `xhost +local:docker` and X11 forwarding | Xvfb sidecar sharing `/tmp/.X11-unix` | same Xvfb sidecar, so both families see the same display |
| `docker run -it` | `docker run --rm` with a timeout | same |
| `turtle_teleop_key` (interactive) | publish to `/turtle1/cmd_vel` | same |

Specs that depend on a mapping: PS-006 (Dockerfile, sudo, rosdep), PS-007 (apt install,
teleop), PS-011 (X11), PS-003 and PS-004 (`-it`).
