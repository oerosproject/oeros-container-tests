# PS-010: Record and play back

Hand-written guide for [`PS-010`](../../specs/PS-010-rosbag.md). Setup and image names are in the
[README](README.md). Tiers: `ros-base`, `perception`, `simulation`, `desktop`, `desktop-full`.

Test: `tests/test_ps010_rosbag.py`. The publisher, recorder and subscriber must share one ROS
graph, so everything runs in one container.

## Steps

1. Start a shell and source the setup:

   ```sh
   docker run -it --rm "$IMAGE" sh
   . /opt/ros/lyrical/setup.sh
   ```

2. Publish on `/chatter` and wait until the topic is visible:

   ```sh
   ros2 topic pub -r 10 /chatter std_msgs/msg/String "{data: hello}" >/dev/null 2>&1 &
   PUB=$!
   until ros2 topic list | grep -q /chatter; do sleep 1; done
   ```

3. Record. In Lyrical `ros2 bag record` needs `--topics` and, without a terminal to read keys
   from, `--disable-keyboard-controls`. Wait for the recorder to subscribe, let it run a few
   seconds, then stop it with SIGTERM:

   ```sh
   ros2 bag record --topics /chatter -o /tmp/bag --disable-keyboard-controls >/tmp/rec.log 2>&1 &
   REC=$!
   until grep -q 'All requested topics are subscribed' /tmp/rec.log; do sleep 1; done
   sleep 4
   kill -TERM $REC; wait $REC
   kill $PUB
   ls /tmp/bag
   ```

   Expected: **AC1**: `/tmp/bag` holds `metadata.yaml` and a storage file (`*.mcap` or
   `*.db3`).

4. Inspect:

   ```sh
   ros2 bag info /tmp/bag; echo "info-exit=$?"
   ```

   Expected: **AC2**: `info-exit=0` and `/chatter` shows a message `Count` of at least 10.

5. Play back to a subscriber. The publisher from step 2 is stopped, so the only source of
   messages is the bag:

   ```sh
   ros2 topic echo --once /chatter std_msgs/msg/String >/tmp/echo.log 2>&1 &
   ECHO=$!
   until ros2 topic info /chatter | grep -q 'Subscription count: 1'; do sleep 1; done
   sleep 1
   ros2 bag play /tmp/bag; echo "play-exit=$?"
   sleep 2; cat /tmp/echo.log
   ```

   Expected: **AC3**: `play-exit=0` and `/tmp/echo.log` contains `data: hello`.

6. Leave with `exit`. `--rm` removes the container.
