"""PS-009: launch files. Desktop tiers, both image families."""

import pytest

from tests.shell import HEADLESS, WAIT_FOR, embed, sections

SCRIPT = (
    WAIT_FOR
    + HEADLESS
    + embed("/tmp/two_turtlesim.launch.py", "two_turtlesim.launch.py")
    + embed("/tmp/talker_launch_test.py", "talker_launch_test.py")
    + """
ros2 launch /tmp/two_turtlesim.launch.py >/tmp/launch.log 2>&1 &
wait_for "ros2 node list | grep -q /turtlesim2/sim" 120 || echo "nodes-not-up"
echo "##STARTED"; grep -c "process started" /tmp/launch.log
echo "##NODES"; ros2 node list
launch_test /tmp/talker_launch_test.py >/tmp/lt.log 2>&1; rc=$?
echo "##LAUNCHTEST"; echo "exit=$rc"; cat /tmp/lt.log
"""
)


@pytest.fixture
def launch_run(ros, tier, family, pytestconfig, run_cache):
    key = ("ps009", tier, family, pytestconfig.getoption("--arch"))
    if key not in run_cache:
        result = ros(SCRIPT, timeout=600)
        assert not result.timed_out, result.output
        run_cache[key] = {"raw": result, **sections(result.stdout)}
    return run_cache[key]


@pytest.mark.spec("PS-009", "AC1")
def test_launch_starts_both_nodes(launch_run):
    assert int(launch_run.get("STARTED", "0").strip() or 0) >= 2, launch_run["raw"].output


@pytest.mark.spec("PS-009", "AC2")
def test_node_list_shows_both(launch_run):
    nodes = launch_run.get("NODES", "").split()
    assert "/turtlesim1/sim" in nodes and "/turtlesim2/sim" in nodes, launch_run["raw"].output


@pytest.mark.spec("PS-009", "AC3")
def test_launch_testing_works(launch_run):
    section = launch_run.get("LAUNCHTEST", "")
    assert "exit=0" in section and "Ran 1 test" in section, launch_run["raw"].output
