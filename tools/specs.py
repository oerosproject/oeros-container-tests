"""Parity spec loader: front matter plus numbered acceptance criteria from specs/PS-*.md."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from tools.matrix import Matrix

ROOT = Path(__file__).resolve().parent.parent
SPEC_DIR = ROOT / "specs"

STATUSES = ("Draft", "Approved", "Implemented", "Verified", "Gap")
# From Approved onwards every criterion must be traced by at least one test.
TRACED_STATUSES = STATUSES[1:]
REQUIRED_FIELDS = ("id", "title", "source", "tiers", "status")

_AC_LINE = re.compile(r"^(AC\d+):\s*(.+)$", re.MULTILINE)
_FRONT_MATTER = re.compile(r"\A---\n(.*?)\n---\n(.*)\Z", re.DOTALL)


class SpecError(Exception):
    pass


@dataclass
class Spec:
    id: str
    title: str
    status: str
    tiers: list[str]
    source: str
    path: Path
    source_sha: str | None = None
    report_only: bool = False
    criteria: dict[str, str] = field(default_factory=dict)

    def applicable_tiers(self, matrix: Matrix) -> list[str]:
        """Expand `all` to the six REP-2001 tiers; keep explicit tier names as written."""
        out: list[str] = []
        for tier in self.tiers:
            for name in matrix.all_tiers if tier == "all" else [tier]:
                if name not in out:
                    out.append(name)
        return out


def parse(path: Path) -> Spec:
    match = _FRONT_MATTER.match(path.read_text())
    if not match:
        raise SpecError(f"{path.name}: missing YAML front matter")
    meta = yaml.safe_load(match.group(1)) or {}
    missing = [name for name in REQUIRED_FIELDS if name not in meta]
    if missing:
        raise SpecError(f"{path.name}: front matter is missing {', '.join(missing)}")
    return Spec(
        id=meta["id"],
        title=meta["title"],
        status=meta["status"],
        tiers=list(meta["tiers"]),
        source=meta["source"],
        source_sha=meta.get("source_sha"),
        report_only=bool(meta.get("report_only", False)),
        path=path,
        criteria=dict(_AC_LINE.findall(match.group(2))),
    )


def load_all(spec_dir: Path = SPEC_DIR) -> dict[str, Spec]:
    specs: dict[str, Spec] = {}
    for path in sorted(spec_dir.glob("PS-*.md")):
        spec = parse(path)
        if spec.id in specs:
            raise SpecError(f"{path.name}: duplicate spec id {spec.id}")
        specs[spec.id] = spec
    return specs
