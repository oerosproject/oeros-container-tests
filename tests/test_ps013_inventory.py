"""PS-013: package inventory parity. Report-only: passes when both sets were captured.

Runs once per tier and probes both families itself, so it is not parametrized by family.
"""

from pathlib import Path

import pytest
import yaml

CONTRACTS = Path(__file__).resolve().parent.parent / "contracts"
TOOLS = ("colcon", "rosdep", "bash", "python3")


def _lines(text: str) -> list[str]:
    return sorted({line.strip() for line in text.splitlines() if line.strip()})


def _capture(ros, probe) -> dict[str, list[str]]:
    packages = ros("ros2 pkg list")
    executables = ros("ros2 pkg executables")
    interfaces = ros("ros2 interface list")
    tools = probe(
        "sh",
        "-c",
        "for t in " + " ".join(TOOLS) + '; do command -v "$t" >/dev/null && echo "$t"; done',
    )
    for result in (packages, executables, interfaces, tools):
        assert result.ok, result.output
    return {
        "packages": _lines(packages.stdout),
        "executables": _lines(executables.stdout),
        "interfaces": [line for line in _lines(interfaces.stdout) if "/" in line],
        "tools": _lines(tools.stdout),
    }


@pytest.fixture
def inventories(ros_for, probe_for):
    return {family: _capture(ros_for(family), probe_for(family)) for family in ("osrf", "oeros")}


def _intended(tier: str, matrix) -> set[tuple[str, str, str]]:
    data = yaml.safe_load((CONTRACTS / "intended-differences.yaml").read_text())
    out = set()
    for entry in data.get("intended") or []:
        tiers = matrix.all_tiers if entry["tiers"] == "all" else entry["tiers"]
        if tier in tiers:
            out.add((entry["kind"], entry["name"], entry["side"]))
    return out


@pytest.mark.spec("PS-013", "AC1")
def test_sets_are_captured(inventories):
    for family, inventory in inventories.items():
        for kind in ("packages", "executables", "interfaces"):
            assert inventory[kind], f"{family}: empty {kind} set"


@pytest.mark.spec("PS-013", "AC2")
def test_difference_artifact(inventories, artifacts, matrix, tier):
    intended = _intended(tier, matrix)
    diff = {}
    for kind in inventories["osrf"]:
        osrf, oeros = set(inventories["osrf"][kind]), set(inventories["oeros"][kind])
        only_osrf, only_oeros = sorted(osrf - oeros), sorted(oeros - osrf)
        diff[kind] = {
            "osrf_count": len(osrf),
            "oeros_count": len(oeros),
            "only_osrf": [n for n in only_osrf if (kind, n, "only_osrf") not in intended],
            "only_oeros": [n for n in only_oeros if (kind, n, "only_oeros") not in intended],
            "intended": [n for n in only_osrf if (kind, n, "only_osrf") in intended]
            + [n for n in only_oeros if (kind, n, "only_oeros") in intended],
        }
    artifacts("inventory-diff", diff)
