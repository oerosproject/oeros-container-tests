"""PS-007: turtlesim nodes, topics, services, parameters, actions. Desktop tiers.

Turtlesim runs on Qt's offscreen platform, so no X server is needed. The interactive teleop
node is replaced by service, parameter and action calls (see specs/step-mapping.md).
"""

import re

import pytest

from tests.shell import HEADLESS, WAIT_FOR, pose, sections

SCRIPT = (
    WAIT_FOR
    + HEADLESS
    + """
ros2 run turtlesim turtlesim_node >/tmp/ts.log 2>&1 &
wait_for "ros2 node list | grep -q /turtlesim" 120 || echo "node-not-up"
echo "##TOPICS"; ros2 topic list
echo "##POSE1"; ros2 topic echo --once /turtle1/pose 2>&1
echo "##TELEPORT"; ros2 service call /turtle1/teleport_absolute turtlesim_msgs/srv/TeleportAbsolute "{x: 2.0, y: 3.0, theta: 0.0}" 2>&1; echo "exit=$?"
echo "##POSE2"; ros2 topic echo --once /turtle1/pose 2>&1
echo "##PARAM"; ros2 param set /turtlesim background_r 255 2>&1; ros2 param get /turtlesim background_r 2>&1
echo "##ACTION"; ros2 action send_goal /turtle1/rotate_absolute turtlesim_msgs/action/RotateAbsolute "{theta: 1.57}" 2>&1; echo "exit=$?"
"""
)


@pytest.fixture
def turtle_run(ros, tier, family, pytestconfig, run_cache):
    key = ("ps007", tier, family, pytestconfig.getoption("--arch"))
    if key not in run_cache:
        result = ros(SCRIPT, timeout=600)
        assert not result.timed_out, result.output
        run_cache[key] = {"raw": result, **sections(result.stdout)}
    return run_cache[key]


@pytest.mark.spec("PS-007", "AC1")
def test_turtlesim_is_present(ros):
    result = ros("ros2 pkg prefix turtlesim")
    assert result.ok, result.output


@pytest.mark.spec("PS-007", "AC2")
def test_expected_topics(turtle_run):
    topics = turtle_run.get("TOPICS", "").split()
    for topic in ("/turtle1/cmd_vel", "/turtle1/pose", "/turtle1/color_sensor"):
        assert topic in topics, turtle_run["raw"].output


@pytest.mark.spec("PS-007", "AC3")
def test_teleport_moves_pose(turtle_run):
    start, end = pose(turtle_run.get("POSE1", "")), pose(turtle_run.get("POSE2", ""))
    assert start and end, turtle_run["raw"].output
    assert (end["x"], end["y"]) == pytest.approx((2.0, 3.0), abs=0.05)
    assert (start["x"], start["y"]) != pytest.approx((end["x"], end["y"]), abs=0.05)


@pytest.mark.spec("PS-007", "AC4")
def test_param_set_takes_effect(turtle_run):
    section = turtle_run.get("PARAM", "")
    assert "Set parameter successful" in section, turtle_run["raw"].output
    assert re.search(r"Integer value is: 255", section), section


@pytest.mark.spec("PS-007", "AC5")
def test_rotate_action_succeeds(turtle_run):
    section = turtle_run.get("ACTION", "")
    assert "Goal finished with status: SUCCEEDED" in section, turtle_run["raw"].output
