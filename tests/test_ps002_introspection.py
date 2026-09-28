"""PS-002: CLI introspection. Runs on every tier, against both image families."""

import pytest


def _lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def _interfaces(text: str) -> list[str]:
    """`ros2 interface list` prints section headers ('Messages:') and indented names."""
    return [line for line in _lines(text) if "/" in line]


@pytest.mark.spec("PS-002", "AC1")
def test_pkg_list(ros):
    result = ros("ros2 pkg list")
    assert result.ok, result.output
    assert {"rclcpp", "rclpy", "std_msgs"} <= set(_lines(result.stdout))


@pytest.mark.spec("PS-002", "AC2")
def test_pkg_executables(ros):
    result = ros("ros2 pkg executables")
    assert result.ok, result.output
    lines = _lines(result.stdout)
    assert lines
    assert all(len(line.split()) == 2 for line in lines), lines[:5]


@pytest.mark.spec("PS-002", "AC3")
def test_interface_list(ros):
    result = ros("ros2 interface list")
    assert result.ok, result.output
    assert "std_msgs/msg/String" in _interfaces(result.stdout)


@pytest.mark.spec("PS-002", "AC4")
def test_capture_inventory(ros, artifacts):
    packages = ros("ros2 pkg list")
    executables = ros("ros2 pkg executables")
    interfaces = ros("ros2 interface list")
    for result in (packages, executables, interfaces):
        assert result.ok, result.output
    inventory = {
        "packages": sorted(_lines(packages.stdout)),
        "executables": sorted(_lines(executables.stdout)),
        "interfaces": sorted(_interfaces(interfaces.stdout)),
    }
    assert all(inventory.values()), {k: len(v) for k, v in inventory.items()}
    artifacts("inventory", inventory)
