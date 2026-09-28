"""PS-005: create and build a package. Dev tier: OSRF ros-base vs oeros ros-dev."""

import pytest

from tests.shell import exit_ok, sections

SCRIPT = """
mkdir -p /tmp/ws/src && cd /tmp/ws/src || exit 1
ros2 pkg create --build-type ament_cmake --node-name my_node my_cmake_pkg >/tmp/create1.log 2>&1; rc=$?
echo "##CREATE_CMAKE"; echo "exit=$rc"
ros2 pkg create --build-type ament_python --node-name my_py_node my_py_pkg >/tmp/create2.log 2>&1; rc=$?
echo "##CREATE_PYTHON"; echo "exit=$rc"
cd /tmp/ws
colcon build >/tmp/build.log 2>&1; rc=$?
echo "##BUILD"; echo "exit=$rc"; tail -n 5 /tmp/build.log
. install/setup.sh
echo "##RUN_CMAKE"; ros2 run my_cmake_pkg my_node; echo "exit=$?"
echo "##RUN_PYTHON"; ros2 run my_py_pkg my_py_node; echo "exit=$?"
"""


@pytest.fixture
def workspace_run(ros, tier, family, pytestconfig, run_cache):
    """Create, build and run the workspace once per cell and share the result."""
    key = ("ps005", tier, family, pytestconfig.getoption("--arch"))
    if key not in run_cache:
        result = ros(SCRIPT, timeout=600)
        assert not result.timed_out, result.output
        run_cache[key] = {"raw": result, **sections(result.stdout)}
    return run_cache[key]


@pytest.mark.spec("PS-005", "AC1")
def test_create_ament_cmake(workspace_run):
    assert exit_ok(workspace_run.get("CREATE_CMAKE", "")), workspace_run["raw"].output


@pytest.mark.spec("PS-005", "AC2")
def test_create_ament_python(workspace_run):
    assert exit_ok(workspace_run.get("CREATE_PYTHON", "")), workspace_run["raw"].output


@pytest.mark.spec("PS-005", "AC3")
def test_colcon_build(workspace_run):
    assert exit_ok(workspace_run.get("BUILD", "")), workspace_run["raw"].output


@pytest.mark.spec("PS-005", "AC4")
def test_overlay_executables_run(workspace_run):
    cmake, python = workspace_run.get("RUN_CMAKE", ""), workspace_run.get("RUN_PYTHON", "")
    assert exit_ok(cmake) and "hello world my_cmake_pkg package" in cmake, workspace_run[
        "raw"
    ].output
    assert exit_ok(python) and "Hi from my_py_pkg." in python, workspace_run["raw"].output
