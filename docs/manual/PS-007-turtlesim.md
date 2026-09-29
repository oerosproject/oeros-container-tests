# PS-007: Turtlesim nodes, topics, services, parameters, actions

Hand-written guide for [`PS-007`](../../specs/PS-007-turtlesim.md). Setup and image names are in
the [README](README.md). Tiers: `desktop`, `desktop-full`.

Test: `tests/test_ps007_turtlesim.py`. The tutorial's interactive `turtle_teleop_key` is
replaced by service, parameter and action calls (see `specs/step-mapping.md`), and turtlesim
runs on Qt's `offscreen` platform, so no X server is needed.

## Start turtlesim

```sh
CONTAINER=ts
docker run -d --name "$CONTAINER" -e QT_QPA_PLATFORM=offscreen "$IMAGE" \
  sh -c '. /opt/ros/lyrical/setup.sh && exec ros2 run turtlesim turtlesim_node'
rosx() { docker exec "$CONTAINER" sh -c ". /opt/ros/lyrical/setup.sh && $*"; }
until rosx 'ros2 node list' | grep -q /turtlesim; do sleep 2; done
```

## Steps

**AC1**: the package is installed.

```sh
rosx 'ros2 pkg prefix turtlesim'
```

Expected: **AC1**: prints a path under `/opt/ros/lyrical` and exits 0.

**AC2**: the topics exist.

```sh
rosx 'ros2 topic list'
```

Expected: **AC2**: the list contains `/turtle1/cmd_vel`, `/turtle1/pose` and
`/turtle1/color_sensor`.

**AC3**: the teleport service moves the turtle.

```sh
rosx 'ros2 topic echo --once /turtle1/pose'
rosx 'ros2 service call /turtle1/teleport_absolute turtlesim_msgs/srv/TeleportAbsolute "{x: 2.0, y: 3.0, theta: 0.0}"'
rosx 'ros2 topic echo --once /turtle1/pose'
```

Expected: **AC3**: the service call succeeds, and the second pose shows `x: 2.0`, `y: 3.0`,
`theta: 0.0` (the first shows the start position near the middle of the window).

**AC4**: a parameter can be set and read back.

```sh
rosx 'ros2 param set /turtlesim background_r 255'
rosx 'ros2 param get /turtlesim background_r'
```

Expected: **AC4**: `param get` returns `Integer value is: 255`.

**AC5**: the rotate action succeeds.

```sh
rosx 'ros2 action send_goal /turtle1/rotate_absolute turtlesim_msgs/action/RotateAbsolute "{theta: 1.57}"'
```

Expected: **AC5**: the goal is accepted and the result reports `Goal finished with status:
SUCCEEDED`.

In Lyrical the turtlesim service and action types live in `turtlesim_msgs`, not `turtlesim`.

## Clean up

```sh
docker rm -f "$CONTAINER"
```
