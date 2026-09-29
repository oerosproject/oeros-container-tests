# PS-008: rclpy publisher script

Hand-written guide for [`PS-008`](../../specs/PS-008-rclpy-script.md). Setup and image names are
in the [README](README.md). Tiers: `desktop`, `desktop-full`.

Test: `tests/test_ps008_rclpy_script.py`. It runs the Docker guide's `move_turtle.py`
(`tests/fixtures/move_turtle.py`, verbatim) against a running turtlesim and compares the pose
before and after. Run from the repository root.

## Start turtlesim with the script mounted

```sh
CONTAINER=ts
docker run -d --name "$CONTAINER" -e QT_QPA_PLATFORM=offscreen \
  -v "$PWD/tests/fixtures/move_turtle.py:/tmp/move_turtle.py:ro" "$IMAGE" \
  sh -c '. /opt/ros/lyrical/setup.sh && exec ros2 run turtlesim turtlesim_node'
rosx() { docker exec "$CONTAINER" sh -c ". /opt/ros/lyrical/setup.sh && $*"; }
until rosx 'ros2 node list' | grep -q /turtlesim; do sleep 2; done
```

With podman on an SELinux host, add `:Z` to the volume option.

## Steps

```sh
rosx 'ros2 topic echo --once /turtle1/pose'      # pose before
rosx 'python3 /tmp/move_turtle.py'; echo "exit=$?"
rosx 'ros2 topic echo --once /turtle1/pose'      # pose after
```

Expected:

- **AC1**: the script runs to completion and `exit=0`.
- **AC2**: the pose after the script differs from the pose before (a `x`, `y` or `theta`
  change of more than about 0.1 in total).

## Clean up

```sh
docker rm -f "$CONTAINER"
```
