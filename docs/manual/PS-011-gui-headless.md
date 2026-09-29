# PS-011: GUI tools, headless

Hand-written guide for [`PS-011`](../../specs/PS-011-gui-headless.md). Setup and image names are
in the [README](README.md). Tiers: `desktop`, `desktop-full`.

Test: `tests/test_ps011_gui.py`. A sidecar container runs Xvfb on display `:99` and shares
`/tmp/.X11-unix` through a volume, which replaces `xhost +local:docker` and host X11
forwarding (see `specs/step-mapping.md`). Both families draw on the same kind of display.
Run from the repository root.

## Start the display

```sh
docker build -t oeros-tests/xvfb:local compose/xvfb
docker volume create ros-x11
docker run -d --name xvfb -v ros-x11:/tmp/.X11-unix oeros-tests/xvfb:local \
  Xvfb :99 -screen 0 1280x800x24 -nolisten tcp -ac
until docker exec xvfb xdpyinfo -display :99 >/dev/null 2>&1; do sleep 1; done
```

## Steps: a tool starts and stays up

Each of AC1 to AC3 starts one tool in the background, waits 10 seconds and checks it is still
running. `TOOL` is the command to run:

```sh
gui() {
  docker run --rm -e DISPLAY=:99 -e QT_X11_NO_MITSHM=1 -v ros-x11:/tmp/.X11-unix "$IMAGE" sh -c "
. /opt/ros/lyrical/setup.sh
$1 >/tmp/gui.log 2>&1 &
PID=\$!
sleep 10
if kill -0 \$PID 2>/dev/null; then echo alive; else echo dead; fi
tail -n 5 /tmp/gui.log
kill \$PID 2>/dev/null"
}
```

```sh
gui 'ros2 run turtlesim turtlesim_node'    # AC1
gui 'ros2 run rqt_gui rqt_gui'             # AC2
gui 'ros2 run rqt_console rqt_console'     # AC3
```

Expected:

- **AC1**: the first line is `alive` for `turtlesim_node`.
- **AC2**: the first line is `alive` for `rqt_gui`. If it is `dead`, the log tail shows
  whether the executable is missing from the image.
- **AC3**: the first line is `alive` for `rqt_console`.

## Step: the screenshot is not blank

**AC4**. Start turtlesim on the display, give the window a moment to paint, then count the
colours in a screenshot taken from the Xvfb container:

```sh
docker run -d --name gui -e DISPLAY=:99 -e QT_X11_NO_MITSHM=1 -v ros-x11:/tmp/.X11-unix "$IMAGE" \
  sh -c '. /opt/ros/lyrical/setup.sh && exec ros2 run turtlesim turtlesim_node'
until docker logs gui 2>&1 | grep -q "Spawning turtle"; do sleep 2; done
sleep 2
docker exec xvfb sh -c 'import -display :99 -window root png:- | identify -format %k png:-'
```

Expected: **AC4**: a number greater than 1. A blank Xvfb root window has one colour;
turtlesim's blue field and the turtle add more.

## Clean up

```sh
docker rm -f gui xvfb
docker volume rm ros-x11
```
