"""PS-010: record and play back. ros-base and up, against both image families."""

import re

import pytest

from tests.shell import WAIT_FOR, sections

# One container run covers record, info and play, because the publisher, recorder and
# subscriber must share a ROS graph. Only portable shell: the oeros base has busybox utilities.
SCRIPT = (
    WAIT_FOR
    + """
ros2 topic pub -r 10 /chatter std_msgs/msg/String "{data: hello}" >/dev/null 2>&1 &
PUB=$!
wait_for "ros2 topic list | grep -q /chatter" 90 || echo "pub-not-visible"
ros2 bag record --topics /chatter -o /tmp/bag --disable-keyboard-controls >/tmp/rec.log 2>&1 &
REC=$!
wait_for "grep -q 'All requested topics are subscribed' /tmp/rec.log" 90 || echo "recorder-not-ready"
sleep 4
kill -TERM $REC
wait $REC
kill $PUB
echo "##LS"; ls /tmp/bag
echo "##INFO"; ros2 bag info /tmp/bag; echo "info-exit=$?"
ros2 topic echo --once /chatter std_msgs/msg/String >/tmp/echo.log 2>&1 &
ECHO=$!
wait_for "ros2 topic info /chatter | grep -q 'Subscription count: 1'" 90 || echo "echo-not-ready"
sleep 1
ros2 bag play /tmp/bag >/tmp/play.log 2>&1
echo "play-exit=$?"
wait_for "grep -q 'data: hello' /tmp/echo.log" 20
kill $ECHO 2>/dev/null
echo "##ECHO"; cat /tmp/echo.log
"""
)


@pytest.fixture
def bag_run(ros, tier, family, pytestconfig, run_cache):
    """Run the record/info/play script once per cell and share the result between tests."""
    key = ("ps010", tier, family, pytestconfig.getoption("--arch"))
    if key not in run_cache:
        result = ros(SCRIPT, timeout=600)
        assert not result.timed_out, result.output
        run_cache[key] = {"raw": result, **sections(result.stdout)}
    return run_cache[key]


@pytest.mark.spec("PS-010", "AC1")
def test_record_writes_bag(bag_run):
    files = bag_run.get("LS", "").split()
    assert "metadata.yaml" in files, bag_run["raw"].output
    assert any(f.endswith((".mcap", ".db3")) for f in files), files


@pytest.mark.spec("PS-010", "AC2")
def test_bag_info_reports_messages(bag_run):
    info = bag_run.get("INFO", "")
    assert "info-exit=0" in info, info
    count = re.search(r"Topic: /chatter .*?Count: (\d+)", info)
    assert count, info
    assert int(count.group(1)) >= 10


@pytest.mark.spec("PS-010", "AC3")
def test_play_republishes(bag_run):
    assert "play-exit=0" in bag_run.get("INFO", ""), bag_run["raw"].output
    assert "data: hello" in bag_run.get("ECHO", ""), bag_run["raw"].output
