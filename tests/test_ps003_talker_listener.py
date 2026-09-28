"""PS-003: talker and listener in one container. Desktop tiers, both image families."""

import pytest

from tests.shell import WAIT_FOR

# Nodes start concurrently. The 15 s budget of AC1 counts from the talker's first message, not
# from container start, which can take far longer on cold or slow storage.
SCRIPT = (
    WAIT_FOR
    + """
ros2 run {pkg} talker >/tmp/talker.log 2>&1 &
ros2 run {pkg} listener >/tmp/listener.log 2>&1 &
wait_for "grep -q Publishing /tmp/talker.log" 120 || echo "talker-not-up"
wait_for 'test "$(grep -c "I heard" /tmp/listener.log)" -ge 3' 15 && echo "heard-ok" || echo "heard-timeout"
echo "##HEARD"; grep "I heard" /tmp/listener.log
"""
)


def _heard(ros, pkg: str):
    # Not str.format: the shell snippets contain braces.
    result = ros(SCRIPT.replace("{pkg}", pkg), timeout=300)
    assert not result.timed_out, result.output
    heard = [line for line in result.stdout.splitlines() if "I heard" in line]
    return result, heard


@pytest.mark.spec("PS-003", "AC1")
def test_cpp_talker_listener(ros):
    result, heard = _heard(ros, "demo_nodes_cpp")
    assert "heard-ok" in result.stdout, result.output
    assert len(heard) >= 3


@pytest.mark.spec("PS-003", "AC2")
def test_python_talker_listener(ros):
    result, heard = _heard(ros, "demo_nodes_py")
    assert "heard-ok" in result.stdout, result.output
    assert len(heard) >= 3
