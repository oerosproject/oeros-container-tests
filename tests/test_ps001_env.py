"""PS-001: environment setup. Runs on every tier, against both image families."""

import pytest

SETUP = "/opt/ros/lyrical"


@pytest.mark.spec("PS-001", "AC1")
def test_ros_env_vars(probe):
    result = probe("sh", "-c", 'echo "$ROS_DISTRO $ROS_VERSION $ROS_PYTHON_VERSION"')
    assert result.ok, result.output
    assert result.stdout.split() == ["lyrical", "2", "3"]


# AC2 and AC3 bypass the entrypoint on purpose: they need a clean shell that has not already
# sourced the setup, and they check that the named shell exists in the image.
@pytest.mark.spec("PS-001", "AC2")
def test_setup_bash_sources_in_bash(probe):
    result = probe("-c", f". {SETUP}/setup.bash", entrypoint="bash")
    assert result.ok, result.output
    assert result.stderr.strip() == ""


@pytest.mark.spec("PS-001", "AC3")
def test_setup_sh_sources_in_sh(probe):
    result = probe("-c", f". {SETUP}/setup.sh", entrypoint="sh")
    assert result.ok, result.output
    assert result.stderr.strip() == ""


@pytest.mark.spec("PS-001", "AC4")
def test_ros2_help_exits_zero(probe):
    result = probe("ros2", "--help")
    assert result.ok, result.output


@pytest.mark.spec("PS-001", "AC5")
def test_entrypoint_sources_setup(probe):
    result = probe("sh", "-c", "command -v ros2")
    assert result.ok, result.output
    assert result.stdout.strip().startswith(f"{SETUP}/"), result.stdout


DOMAIN_ID_SCRIPT = """
import rclpy
context = rclpy.Context()
rclpy.init(context=context)
print(context.get_domain_id())
context.try_shutdown()
"""


@pytest.mark.spec("PS-001", "AC6")
def test_ros_domain_id_is_honored(probe):
    result = probe("python3", "-c", DOMAIN_ID_SCRIPT, env={"ROS_DOMAIN_ID": "42"})
    assert result.ok, result.output
    assert result.stdout.strip().splitlines()[-1] == "42"


@pytest.mark.spec("PS-001", "AC8")
def test_default_rmw_is_recorded(ros, artifacts):
    result = ros("ros2 doctor --report 2>&1 | grep 'middleware name'")
    assert result.ok, result.output
    rmw = result.stdout.split(":", 1)[1].strip()
    assert rmw.startswith("rmw_"), result.stdout
    artifacts("rmw", {"default_rmw_implementation": rmw})
