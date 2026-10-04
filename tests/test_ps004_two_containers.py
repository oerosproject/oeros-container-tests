"""PS-004: talker and listener in two containers. Desktop tiers.

AC1 and AC2 run per family. AC3 to AC6 pair two images, so they run once per tier and
probe both images themselves. Cross-family runs pin the middleware explicitly, because the two
families may default to different implementations (PS-001 records each default).
"""

import time
import uuid
from pathlib import Path

import pytest

# Pinned for the cross-family pairs only. Both families default to Fast DDS today.
INTEROP_RMW = "rmw_fastrtps_cpp"
BUDGET = 15  # seconds from the talker's first message, as in PS-003


def _node(pkg_exe: str) -> list[str]:
    return ["sh", "-c", f". /opt/ros/lyrical/setup.sh && exec ros2 run {pkg_exe}"]


def _pair(scenario, talker_image: str, listener_image: str, env: dict[str, str]):
    """Start a talker and a listener on the scenario network; return (talker, listener)."""
    talker = scenario.start(talker_image, _node("demo_nodes_cpp talker"), "talker", env=env)
    listener = scenario.start(listener_image, _node("demo_nodes_cpp listener"), "listener", env=env)
    return talker, listener


def _assert_heard(scenario, talker: str, listener: str) -> None:
    assert scenario.wait_log(talker, "Publishing", timeout=180), scenario.runtime.logs(talker)
    assert scenario.wait_log(listener, "I heard", count=3, timeout=BUDGET), (
        f"listener logs:\n{scenario.runtime.logs(listener)}\ntalker logs:\n"
        f"{scenario.runtime.logs(talker)}"
    )


def _env() -> dict[str, str]:
    # A domain id per test keeps concurrent scenarios apart (valid range 0-101).
    return {"ROS_DOMAIN_ID": str(uuid.uuid4().int % 100)}


@pytest.mark.spec("PS-004", "AC1")
@pytest.mark.multi_container
def test_docker_run_pair(scenario, image):
    talker, listener = _pair(scenario, image, image, _env())
    _assert_heard(scenario, talker, listener)


@pytest.mark.spec("PS-004", "AC2")
@pytest.mark.multi_container
def test_compose_pair(runtime, image):
    compose = runtime.compose_command()
    if compose is None:
        pytest.skip("no compose provider (install podman-compose or docker compose)")
    project = f"oeros-tl-{uuid.uuid4().hex[:8]}"
    file = str(Path(__file__).resolve().parent.parent / "compose" / "talker-listener.yaml")
    env = {
        **runtime.env,
        "TALKER_IMAGE": image,
        "LISTENER_IMAGE": image,
        "ROS_DOMAIN_ID": _env()["ROS_DOMAIN_ID"],
        "COMPOSE_PROJECT_NAME": project,
    }
    base = [*compose, "-p", project, "-f", file]
    up = runtime.exec_env([*base, "up", "-d"], env, timeout=600)
    try:
        assert up.ok, up.output
        deadline = time.monotonic() + 180
        heard = 0
        while time.monotonic() < deadline and heard < 3:
            time.sleep(2)
            logs = runtime.exec_env([*base, "logs", "listener"], env, timeout=60).output
            heard = logs.count("I heard")
        assert heard >= 3, logs
    finally:
        runtime.exec_env([*base, "down", "-v", "-t", "1"], env, timeout=300)


@pytest.mark.spec("PS-004", "AC3")
@pytest.mark.multi_container
def test_oeros_talker_osrf_listener(scenario, image_for):
    env = {**_env(), "RMW_IMPLEMENTATION": INTEROP_RMW}
    talker, listener = _pair(scenario, image_for("oeros"), image_for("osrf"), env)
    _assert_heard(scenario, talker, listener)


@pytest.mark.spec("PS-004", "AC4")
@pytest.mark.multi_container
def test_osrf_talker_oeros_listener(scenario, image_for):
    env = {**_env(), "RMW_IMPLEMENTATION": INTEROP_RMW}
    talker, listener = _pair(scenario, image_for("osrf"), image_for("oeros"), env)
    _assert_heard(scenario, talker, listener)


@pytest.mark.spec("PS-004", "AC5")
@pytest.mark.multi_container
@pytest.mark.compares("sloretz")
def test_oeros_talker_sloretz_listener(scenario, image_for):
    env = {**_env(), "RMW_IMPLEMENTATION": INTEROP_RMW}
    talker, listener = _pair(scenario, image_for("oeros"), image_for("sloretz"), env)
    _assert_heard(scenario, talker, listener)


@pytest.mark.spec("PS-004", "AC6")
@pytest.mark.multi_container
@pytest.mark.compares("sloretz")
def test_sloretz_talker_oeros_listener(scenario, image_for):
    env = {**_env(), "RMW_IMPLEMENTATION": INTEROP_RMW}
    talker, listener = _pair(scenario, image_for("sloretz"), image_for("oeros"), env)
    _assert_heard(scenario, talker, listener)
