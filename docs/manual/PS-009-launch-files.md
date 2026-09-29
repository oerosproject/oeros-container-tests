# PS-009: Launch files

Hand-written guide for [`PS-009`](../../specs/PS-009-launch-files.md). Setup and image names are
in the [README](README.md). Tiers: `desktop`, `desktop-full`.

Test: `tests/test_ps009_launch.py`. It launches `tests/fixtures/two_turtlesim.launch.py` (two
turtlesim nodes, after the launch tutorial) and runs `tests/fixtures/talker_launch_test.py`
with `launch_test`. Neither family ships `launch_pytest`, so the suite uses `launch_testing`.
Run from the repository root.

## Start the launch file

```sh
CONTAINER=launch
docker run -d --name "$CONTAINER" -e QT_QPA_PLATFORM=offscreen \
  -v "$PWD/tests/fixtures:/fixtures:ro" "$IMAGE" \
  sh -c '. /opt/ros/lyrical/setup.sh && exec ros2 launch /fixtures/two_turtlesim.launch.py'
rosx() { docker exec "$CONTAINER" sh -c ". /opt/ros/lyrical/setup.sh && $*"; }
until rosx 'ros2 node list' | grep -q /turtlesim2/sim; do sleep 2; done
```

## Steps

**AC1**: both processes started.

```sh
docker logs "$CONTAINER" 2>&1 | grep -c "process started"
```

Expected: **AC1**: 2 or more.

**AC2**: both nodes are visible.

```sh
rosx 'ros2 node list'
```

Expected: **AC2**: the list contains `/turtlesim1/sim` and `/turtlesim2/sim`.

**AC3**: `launch_test` runs a launch_testing test.

```sh
rosx 'launch_test /fixtures/talker_launch_test.py'; echo "exit=$?"
```

Expected: **AC3**: `exit=0` and the output contains `Ran 1 test`. The test launches the C++
talker and waits for `Publishing`.

## Clean up

```sh
docker rm -f "$CONTAINER"
```
