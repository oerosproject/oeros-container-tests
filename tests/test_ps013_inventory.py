"""PS-013: package inventory parity. Report-only: passes when every set was captured.

Runs once per tier and probes every family the tier publishes, so it is not parametrized by
family. OSRF is the reference; each other family is diffed against it.
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
def inventories(ros_for, probe_for, matrix, tier):
    return {
        family: _capture(ros_for(family), probe_for(family)) for family in matrix.families(tier)
    }


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


def _diff(reference: dict, candidate: dict, family: str, intended: set) -> dict:
    diff = {}
    for kind in reference:
        ref, cand = set(reference[kind]), set(candidate[kind])
        only_ref, only_cand = sorted(ref - cand), sorted(cand - ref)
        side_ref, side_cand = "only_osrf", f"only_{family}"
        diff[kind] = {
            "reference_count": len(ref),
            "candidate_count": len(cand),
            "only_reference": [n for n in only_ref if (kind, n, side_ref) not in intended],
            "only_candidate": [n for n in only_cand if (kind, n, side_cand) not in intended],
            "intended": [n for n in only_ref if (kind, n, side_ref) in intended]
            + [n for n in only_cand if (kind, n, side_cand) in intended],
        }
    return diff


@pytest.mark.spec("PS-013", "AC2")
def test_difference_artifact(inventories, artifacts, matrix, tier):
    intended = _intended(tier, matrix)
    for family, inventory in inventories.items():
        if family != "osrf":
            artifacts(
                f"inventory-diff-{family}", _diff(inventories["osrf"], inventory, family, intended)
            )
