"""PS-011: GUI tools, headless, on a shared Xvfb display. Desktop tiers, both families.

The Xvfb sidecar (compose/xvfb/Dockerfile) owns display :99 and shares /tmp/.X11-unix through
a volume, so both image families draw on the same kind of display. This replaces `xhost
+local:docker` and host X11 forwarding (see specs/step-mapping.md).
"""

import time
from pathlib import Path

import pytest

XVFB_CONTEXT = Path(__file__).resolve().parent.parent / "compose" / "xvfb"
XVFB_IMAGE = "oeros-tests/xvfb:local"
DISPLAY = ":99"
GUI_ENV = {"DISPLAY": DISPLAY, "QT_X11_NO_MITSHM": "1"}
STAY_UP = 10  # seconds a GUI tool must survive


@pytest.fixture(scope="session")
def xvfb_image(runtime):
    if not runtime.has_image(f"localhost/{XVFB_IMAGE}"):
        runtime.build(XVFB_IMAGE, str(XVFB_CONTEXT))
    return XVFB_IMAGE


@pytest.fixture
def display(scenario, runtime, xvfb_image):
    """A running Xvfb sidecar; returns the volume that carries its X11 socket."""
    volume = scenario.x11_volume()
    scenario.start(
        xvfb_image,
        ["Xvfb", DISPLAY, "-screen", "0", "1280x800x24", "-nolisten", "tcp", "-ac"],
        "xvfb",
        volumes=[f"{volume}:/tmp/.X11-unix"],
    )
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if runtime.exec(f"oeros-xvfb-{scenario.id}", ["xdpyinfo", "-display", DISPLAY]).ok:
            return volume
        time.sleep(1)
    pytest.fail(f"Xvfb did not come up:\n{runtime.logs(f'oeros-xvfb-{scenario.id}')}")


def _stays_up(ros, volume: str, command: str) -> None:
    result = ros(
        f"""{command} >/tmp/gui.log 2>&1 &
PID=$!
sleep {STAY_UP}
if kill -0 $PID 2>/dev/null; then echo alive; else echo dead; fi
tail -n 5 /tmp/gui.log
kill $PID 2>/dev/null
""",
        env=GUI_ENV,
        volumes=[f"{volume}:/tmp/.X11-unix"],
        timeout=300,
    )
    assert result.stdout.startswith("alive"), result.output


@pytest.mark.spec("PS-011", "AC1")
@pytest.mark.gui
def test_turtlesim_starts(ros, display):
    _stays_up(ros, display, "ros2 run turtlesim turtlesim_node")


@pytest.mark.spec("PS-011", "AC2")
@pytest.mark.gui
def test_rqt_gui_starts(ros, display):
    _stays_up(ros, display, "ros2 run rqt_gui rqt_gui")


@pytest.mark.spec("PS-011", "AC3")
@pytest.mark.gui
def test_rqt_console_starts(ros, display):
    _stays_up(ros, display, "ros2 run rqt_console rqt_console")


@pytest.mark.spec("PS-011", "AC4")
@pytest.mark.gui
def test_screenshot_is_not_blank(scenario, runtime, image, display):
    ros_container = scenario.start(
        image,
        ["sh", "-c", ". /opt/ros/lyrical/setup.sh && exec ros2 run turtlesim turtlesim_node"],
        "gui",
        env=GUI_ENV,
        volumes=[f"{display}:/tmp/.X11-unix"],
    )
    assert scenario.wait_log(ros_container, "Spawning turtle", timeout=180), runtime.logs(
        ros_container
    )
    time.sleep(2)  # let the window paint
    xvfb = f"oeros-xvfb-{scenario.id}"
    shot = runtime.exec(
        xvfb,
        ["sh", "-c", f"import -display {DISPLAY} -window root png:- | identify -format %k png:-"],
    )
    assert shot.ok, shot.output
    # A blank Xvfb root window has one colour; turtlesim's blue field and turtle add more.
    assert int(shot.stdout.strip()) > 1, f"screenshot has {shot.stdout.strip()} colour(s)"
