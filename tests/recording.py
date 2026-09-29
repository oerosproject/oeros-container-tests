"""Records the commands a test run sends to the container runtime (see tools/gen_manual.py)."""

from __future__ import annotations

events: list[dict] | None = None
_families: dict[str, str] = {}
_current: dict = {}


def start() -> None:
    global events
    events = []


def note_image(ref: str, family: str) -> None:
    _families[ref] = family


def begin_test(spec: str | None, criteria: list[str], tier: str | None) -> None:
    _current.clear()
    _current.update(spec=spec, criteria=criteria, tier=tier)
    if events is not None:
        events.append({"event": "test", **_current})


def note_run(
    ref: str,
    cmd: list[str],
    env: dict[str, str] | None,
    entrypoint: str | None,
    volumes: list[str] | None,
) -> None:
    if events is None:
        return
    events.append(
        {
            "event": "run",
            "spec": _current.get("spec"),
            "tier": _current.get("tier"),
            "family": _families.get(ref),
            "env": dict(env or {}),
            "entrypoint": entrypoint,
            "volumes": list(volumes or []),
            "cmd": list(cmd),
        }
    )
