# PS-003: Talker and listener in one container

Hand-written guide for [`PS-003`](../../specs/PS-003-talker-listener-single.md). Setup and image
names are in the [README](README.md). Tiers: `desktop`, `desktop-full`.

Test: `tests/test_ps003_talker_listener.py`. It starts both nodes in one container and counts
`I heard` lines from the listener.

## Steps

1. Start a shell in the image and source the ROS setup:

   ```sh
   docker run -it --rm "$IMAGE" sh
   . /opt/ros/lyrical/setup.sh
   ```

2. **AC1** (C++ nodes). Start both nodes in the background and wait for the talker's first
   message:

   ```sh
   ros2 run demo_nodes_cpp talker >/tmp/talker.log 2>&1 &
   ros2 run demo_nodes_cpp listener >/tmp/listener.log 2>&1 &
   until grep -q Publishing /tmp/talker.log; do sleep 1; done
   ```

   A cold container start can take many seconds, so the wait has no timeout here. The
   15 second budget starts from the talker's first message, not from `docker run`.

3. Within 15 seconds of that first message, count what the listener heard:

   ```sh
   sleep 5; grep "I heard" /tmp/listener.log
   ```

   Expected: **AC1**: the listener logs 3 or more `I heard` lines.

4. **AC2** (Python nodes). Stop the C++ nodes and repeat with `demo_nodes_py`:

   ```sh
   kill %1 %2
   ros2 run demo_nodes_py talker >/tmp/talker.log 2>&1 &
   ros2 run demo_nodes_py listener >/tmp/listener.log 2>&1 &
   until grep -q Publishing /tmp/talker.log; do sleep 1; done
   sleep 5; grep "I heard" /tmp/listener.log
   ```

   Expected: **AC2**: 3 or more `I heard` lines with the rclpy talker and listener.

5. Leave the shell with `exit`. `--rm` removes the container.

If both families print `I heard` lines but the count differs by a message or two, that is
timing, not a difference. If one family prints none, check `/tmp/listener.log` for an RMW or
discovery error.
