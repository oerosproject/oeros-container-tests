"""Matrix fixtures, spec-driven parametrization and known-gap handling.

A test names its spec with `@pytest.mark.spec("PS-001", "AC1")` and takes the `tier`,
`family` and `image`/`probe` fixtures. The spec's front matter decides which tiers exist for
the test, so tests never list tiers themselves. Both families run the same test body.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path

import pytest
import yaml

from tests.plugins.spec_trace import RESULTS_DIR, spec_markers
from tests.runtime import ProbeResult, Runtime
from tools import matrix as matrixmod
from tools import specs as specmod

ROOT = Path(__file__).resolve().parent.parent
FAMILIES = matrixmod.FAMILIES


@pytest.fixture(scope="session")
def matrix() -> matrixmod.Matrix:
    return matrixmod.load(ROOT / "images.yaml")


@pytest.fixture(scope="session")
def runtime() -> Runtime:
    return Runtime()


@pytest.fixture(scope="session")
def platform_name(pytestconfig: pytest.Config) -> str:
    return f"linux/{pytestconfig.getoption('--arch')}"


@pytest.fixture(scope="session")
def _pulled() -> set[tuple[str, str]]:
    return set()


@pytest.fixture
def image_for(request, matrix, tier, runtime, platform_name, _pulled):
    """Return resolve(family) -> image ref, pulling or checking the image on first use."""

    def resolve(family: str) -> str:
        arch = platform_name.split("/")[1]
        try:
            ref = matrixmod.image_ref(matrix, family, tier, arch=arch)
        except matrixmod.MatrixError as exc:
            pytest.fail(str(exc), pytrace=False)
        request.node.user_properties.append((f"image:{family}", ref))
        if (ref, platform_name) not in _pulled:
            if family == "oeros" and os.environ.get("OEROS_SOURCE", "registry") == "local":
                if not runtime.has_image(ref):
                    pytest.fail(
                        f"OEROS_SOURCE=local but {ref} is not loaded; "
                        f"run: python -m tools.load_oeros --tier {tier} --arch {arch}",
                        pytrace=False,
                    )
            else:
                pull = runtime.pull(ref, platform_name)
                if not pull.ok:
                    pytest.fail(
                        f"cannot pull {ref} ({platform_name}):\n{pull.output}", pytrace=False
                    )
            _pulled.add((ref, platform_name))
        return ref

    return resolve


@pytest.fixture
def image(image_for, family) -> str:
    """The image for this test's tier and family."""
    return image_for(family)


@pytest.fixture
def probe_for(image_for, runtime, platform_name):
    """Return probe(family) -> run(*cmd, ...) for tests that compare both families."""

    def bind(family: str):
        ref = image_for(family)

        def run(
            *cmd: str,
            env: dict[str, str] | None = None,
            entrypoint: str | None = None,
            volumes: list[str] | None = None,
            timeout: float = 60,
        ) -> ProbeResult:
            return runtime.run(
                ref,
                list(cmd),
                platform=platform_name,
                env=env,
                entrypoint=entrypoint,
                volumes=volumes,
                timeout=timeout,
            )

        return run

    return bind


@pytest.fixture
def probe(probe_for, family):
    """Run a command through the image's entrypoint and return its ProbeResult."""
    return probe_for(family)


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    names = [n for n in ("tier", "family") if n in metafunc.fixturenames]
    if not names:
        return
    spec_id, _ = spec_markers(metafunc.definition)
    if spec_id is None:
        raise pytest.UsageError(f"{metafunc.definition.nodeid}: test has no @pytest.mark.spec")
    specs = specmod.load_all(ROOT / "specs")
    if spec_id not in specs:
        raise pytest.UsageError(f"{metafunc.definition.nodeid}: unknown spec {spec_id}")
    matrix = matrixmod.load(ROOT / "images.yaml")
    tiers = specs[spec_id].applicable_tiers(matrix)
    for tier in tiers:
        matrix.entry(tier)  # fail collection on a tier the matrix does not define

    if names == ["tier", "family"]:
        cells = [(t, f) for t in tiers for f in FAMILIES]
        metafunc.parametrize("tier,family", cells, ids=[f"{t}-{f}" for t, f in cells])
    elif names == ["tier"]:
        metafunc.parametrize("tier", tiers)
    else:
        metafunc.parametrize("family", FAMILIES)


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    want_tiers = config.getoption("--tier")
    want_families = config.getoption("--family")
    want_specs = config.getoption("--spec")
    gaps = _load_gaps()

    kept, dropped = [], []
    for item in items:
        params = item.callspec.params if hasattr(item, "callspec") else {}
        spec_id, criteria = spec_markers(item)
        if (
            (want_tiers and params.get("tier") not in want_tiers)
            or (want_families and params.get("family") not in want_families)
            or (want_specs and spec_id not in want_specs)
        ):
            dropped.append(item)
            continue
        kept.append(item)
        if params.get("family") == "oeros":
            for gap in gaps:
                if (
                    gap["spec"] == spec_id
                    and gap["criterion"] in criteria
                    and gap["tier"] in ("all", params.get("tier"))
                ):
                    item.add_marker(
                        pytest.mark.xfail(
                            strict=True, reason=f"{gap['issue']}: {gap.get('reason', '')}"
                        )
                    )
    if dropped:
        config.hook.pytest_deselected(items=dropped)
        items[:] = kept


def _load_gaps() -> list[dict]:
    data = yaml.safe_load((ROOT / "gaps.yaml").read_text()) or {}
    return data.get("gaps") or []


ROS_SETUP = "/opt/ros/lyrical/setup.sh"


def ros_runner(probe):
    def run(script: str, **kwargs):
        # A newline, not `&&`: a script that backgrounds its first command would otherwise
        # background the `.` with it and leave the main shell without the environment.
        return probe("sh", "-c", f". {ROS_SETUP} || exit 1\n{script}", **kwargs)

    return run


@pytest.fixture
def ros_for(probe_for):
    """Return ros(family) -> ros-sourcing runner, for tests that compare both families."""
    return lambda family: ros_runner(probe_for(family))


@pytest.fixture
def ros(probe):
    """Run a shell script with the ROS setup sourced explicitly.

    Most specs measure a capability (bags, introspection, ...), so they must not depend on the
    image's entrypoint setting up the environment. PS-001 covers the entrypoint itself.
    """

    return ros_runner(probe)


@pytest.fixture
def artifacts(request, pytestconfig):
    """Write a JSON artifact under results/<run-id>/artifacts/<tier>-<family>-<arch>/."""

    def write(name: str, data) -> Path:
        params = request.node.callspec.params
        cell = f"{params['tier']}-{params.get('family', 'both')}-{pytestconfig.getoption('--arch')}"
        path = pytestconfig.stash[RESULTS_DIR] / "artifacts" / cell / f"{name}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
        return path

    return write


@pytest.fixture(scope="session")
def run_cache() -> dict:
    """Results of multi-step probe runs, shared by the tests of one spec for one cell."""
    return {}


class Scenario:
    """A unique network plus the containers started on it; everything is removed afterwards."""

    def __init__(self, runtime: Runtime, platform_name: str):
        self.runtime = runtime
        self.platform = platform_name
        self.id = uuid.uuid4().hex[:8]
        self.network = f"oeros-net-{self.id}"
        self.volume = f"oeros-x11-{self.id}"
        self._containers: list[str] = []
        self._volume_created = False
        runtime.network_create(self.network)

    def start(self, ref: str, cmd: list[str], role: str, **kwargs) -> str:
        name = f"oeros-{role}-{self.id}"
        self.runtime.start(
            ref, cmd, name=name, platform=self.platform, network=self.network, **kwargs
        )
        self._containers.append(name)
        return name

    def x11_volume(self) -> str:
        if not self._volume_created:
            self.runtime.volume_create(self.volume)
            self._volume_created = True
        return self.volume

    def wait_log(self, name: str, needle: str, count: int = 1, timeout: float = 60) -> bool:
        """Poll a container's log until `needle` appears `count` times."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.runtime.logs(name).count(needle) >= count:
                return True
            time.sleep(1)
        return False

    def close(self) -> None:
        self.runtime.remove(*reversed(self._containers))
        self.runtime.network_rm(self.network)
        if self._volume_created:
            self.runtime.volume_rm(self.volume)


@pytest.fixture
def scenario(runtime, platform_name):
    """Multi-container scenario with its own network (and, on demand, an X11 volume)."""
    scenario = Scenario(runtime, platform_name)
    try:
        yield scenario
    finally:
        scenario.close()
