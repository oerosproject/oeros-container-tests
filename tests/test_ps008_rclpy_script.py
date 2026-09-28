"""PS-008: the Docker guide's move_turtle.py rclpy script. Desktop tiers, both families."""

import pytest

from tests.shell import HEADLESS, WAIT_FOR, embed, pose, sections

SCRIPT = (
    WAIT_FOR
    + HEADLESS
    + embed("/tmp/move_turtle.py", "move_turtle.py")
    + """
ros2 run turtlesim turtlesim_node >/tmp/ts.log 2>&1 &
wait_for "ros2 node list | grep -q /turtlesim" 120 || echo "node-not-up"
echo "##POSE1"; ros2 topic echo --once /turtle1/pose 2>&1
python3 /tmp/move_turtle.py >/tmp/move.log 2>&1; rc=$?
echo "##RUN"; echo "exit=$rc"; cat /tmp/move.log
echo "##POSE2"; ros2 topic echo --once /turtle1/pose 2>&1
"""
)


@pytest.fixture
def move_run(ros, tier, family, pytestconfig, run_cache):
    key = ("ps008", tier, family, pytestconfig.getoption("--arch"))
    if key not in run_cache:
        result = ros(SCRIPT, timeout=600)
        assert not result.timed_out, result.output
        run_cache[key] = {"raw": result, **sections(result.stdout)}
    return run_cache[key]


@pytest.mark.spec("PS-008", "AC1")
def test_script_runs_to_completion(move_run):
    assert "exit=0" in move_run.get("RUN", ""), move_run["raw"].output


@pytest.mark.spec("PS-008", "AC2")
def test_pose_changes(move_run):
    start, end = pose(move_run.get("POSE1", "")), pose(move_run.get("POSE2", ""))
    assert start and end, move_run["raw"].output
    moved = (
        abs(end["x"] - start["x"]) + abs(end["y"] - start["y"]) + abs(end["theta"] - start["theta"])
    )
    assert moved > 0.1, (start, end)
