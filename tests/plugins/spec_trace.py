"""Traceability and parity collector.

Every test carries `@pytest.mark.spec("PS-003", "AC2")`. This plugin records one result per
(spec, criterion, tier, family) and writes two files into the results directory:

  traceability.json  criterion -> tests -> outcomes
  parity.json        flat records that tools/parity_report.py turns into the matrix

Static checks (unknown criteria, criteria without a test) live in tools/spec_lint.py, which
does not need Docker.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests import recording

RESULTS_DIR = pytest.StashKey[Path]()
ARCH = pytest.StashKey[str]()
_META = pytest.StashKey[dict]()
_RECORDS = pytest.StashKey[dict]()


def spec_markers(item: pytest.Item) -> tuple[str | None, list[str]]:
    """Return (spec id, criteria) from an item's spec markers."""
    spec_id, criteria = None, []
    for marker in item.iter_markers("spec"):
        if not marker.args:
            continue
        spec_id = spec_id or marker.args[0]
        criteria += [ac for ac in marker.args[1:] if ac not in criteria]
    return spec_id, criteria


def outcome_of(rep: pytest.TestReport) -> str | None:
    """Map a report phase to a parity outcome; None means this phase decides nothing."""
    if rep.when == "setup":
        if rep.failed:
            return "error"
        if rep.skipped:
            return "xfailed" if hasattr(rep, "wasxfail") else "skipped"
        return None
    if rep.when == "call":
        if hasattr(rep, "wasxfail"):
            return "xfailed" if rep.skipped else "xpassed"
        if rep.failed:
            return "xpass-strict" if "XPASS(strict)" in str(rep.longrepr) else "failed"
        return rep.outcome
    return None


@pytest.hookimpl(trylast=True)
def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    meta = {}
    for item in items:
        spec_id, criteria = spec_markers(item)
        params = item.callspec.params if hasattr(item, "callspec") else {}
        meta[item.nodeid] = {
            "spec": spec_id,
            "criteria": criteria,
            "tier": params.get("tier"),
            "family": params.get("family"),
        }
    config.stash[_META] = meta
    config.stash[_RECORDS] = {}


def pytest_runtest_setup(item: pytest.Item) -> None:
    spec_id, criteria = spec_markers(item)
    params = item.callspec.params if hasattr(item, "callspec") else {}
    recording.begin_test(spec_id, criteria, params.get("tier"))


def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    outcome = outcome_of(report)
    if outcome is None:
        return
    config = _current_config()
    meta = config.stash.get(_META, {}).get(report.nodeid)
    if not meta or not meta["spec"]:
        return
    props = dict(report.user_properties)
    image = props.get("image:" + str(meta["family"])) or ", ".join(
        value for key, value in props.items() if key.startswith("image:")
    )
    reason = getattr(report, "wasxfail", None)
    if reason is None and report.failed:
        crash = getattr(report.longrepr, "reprcrash", None)
        if crash is not None:
            lines = [line.strip() for line in crash.message.splitlines() if line.strip()]
            reason = " ".join(lines[:2])[:200]
    if reason is None and report.skipped and isinstance(report.longrepr, tuple):
        reason = str(report.longrepr[2]).removeprefix("Skipped: ")
    config.stash[_RECORDS][report.nodeid] = {
        **meta,
        "arch": config.stash.get(ARCH, None),
        "image": image or None,
        "outcome": outcome,
        "reason": reason,
        "duration": round(report.duration, 3),
    }


def pytest_sessionfinish(session: pytest.Session) -> None:
    config = session.config
    records = config.stash.get(_RECORDS, {})
    results_dir = config.stash.get(RESULTS_DIR, None)
    if not records or results_dir is None:
        return
    results_dir.mkdir(parents=True, exist_ok=True)
    if recording.events is not None:
        (results_dir / "commands.json").write_text(json.dumps(recording.events, indent=1) + "\n")

    parity = []
    trace: dict[str, list[dict]] = {}
    for nodeid, rec in sorted(records.items()):
        for criterion in rec["criteria"] or [None]:
            parity.append(
                {
                    "spec": rec["spec"],
                    "criterion": criterion,
                    "tier": rec["tier"],
                    "family": rec["family"],
                    "arch": rec["arch"],
                    "image": rec["image"],
                    "outcome": rec["outcome"],
                    "reason": rec["reason"],
                    "nodeid": nodeid,
                }
            )
            key = f"{rec['spec']}/{criterion}" if criterion else str(rec["spec"])
            trace.setdefault(key, []).append(
                {
                    "nodeid": nodeid,
                    "tier": rec["tier"],
                    "family": rec["family"],
                    "outcome": rec["outcome"],
                }
            )
    (results_dir / "parity.json").write_text(json.dumps(parity, indent=2) + "\n")
    (results_dir / "traceability.json").write_text(
        json.dumps(trace, indent=2, sort_keys=True) + "\n"
    )

    latest = results_dir.parent / "latest"
    try:
        if latest.is_symlink() or latest.exists():
            latest.unlink()
        latest.symlink_to(results_dir.name)
    except OSError:
        pass  # a missing convenience link must not fail the run


_config: pytest.Config | None = None


def pytest_configure(config: pytest.Config) -> None:
    global _config
    _config = config
    if config.getoption("--record-commands", default=False):
        recording.start()


def _current_config() -> pytest.Config:
    assert _config is not None
    return _config
