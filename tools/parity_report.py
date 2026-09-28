"""Turn parity.json files into the parity matrix: specs as rows, tiers as columns.

    python -m tools.parity_report [RESULTS_DIR ...] [--out DIR]

Several results directories (one per CI cell) are merged. Writes parity.md and parity.html into
--out (default: the first results directory) and prints the Markdown.
"""

from __future__ import annotations

import argparse
import html
import json
import sys
from collections import defaultdict
from pathlib import Path

from tools import matrix as matrixmod
from tools import specs as specmod

ROOT = Path(__file__).resolve().parent.parent

# Worst first. A cell shows the worst state among its criteria.
PARITY = "parity"
KNOWN_GAP = "known-gap"
NEW_GAP = "new-gap"
REFERENCE_BROKEN = "reference-broken"
NOT_RUN = "not-run"
NOT_APPLICABLE = "n/a"
REPORT_ONLY = "report-only"
SEVERITY = [REFERENCE_BROKEN, NEW_GAP, KNOWN_GAP, NOT_RUN, PARITY]

LABELS = {
    PARITY: ("✅", "parity met"),
    KNOWN_GAP: ("🟡", "known gap"),
    NEW_GAP: ("❌", "new gap"),
    REFERENCE_BROKEN: ("🛑", "reference broken"),
    NOT_RUN: ("⚪", "not run"),
    REPORT_ONLY: ("📋", "report only"),
    NOT_APPLICABLE: ("—", "not applicable"),
}

FAILING = {"failed", "error", "xpass-strict"}


def load_records(dirs: list[Path]) -> list[dict]:
    records: list[dict] = []
    for directory in dirs:
        path = directory / "parity.json"
        if not path.exists():
            print(f"parity_report: no parity.json in {directory}", file=sys.stderr)
            continue
        records += json.loads(path.read_text())
    return records


def cross_state(outcomes: list[str]) -> str:
    """State of a criterion that pairs both families in one test (there is no separate OSRF run)."""
    if any(o in FAILING for o in outcomes):
        return NEW_GAP
    if any(o in ("xfailed", "xpassed") for o in outcomes):
        return KNOWN_GAP
    return PARITY if outcomes and all(o == "passed" for o in outcomes) else NOT_RUN


def load_inventory(dirs: list[Path]) -> dict[str, dict]:
    """PS-013 difference artifacts, keyed by tier (results/<run>/artifacts/<tier>-both-<arch>/)."""
    out: dict[str, dict] = {}
    for directory in dirs:
        for path in sorted(directory.glob("artifacts/*-both-*/inventory-diff.json")):
            tier = path.parent.name.rsplit("-both-", 1)[0]
            out[tier] = json.loads(path.read_text())
    return out


def criterion_state(osrf: list[str], oeros: list[str]) -> str:
    """Compare one criterion's outcomes (across arches) for the two families."""
    if not osrf or not oeros:
        return NOT_RUN
    if any(o in FAILING for o in osrf):
        return REFERENCE_BROKEN
    if any(o in FAILING for o in oeros):
        return NEW_GAP
    if any(o in ("xfailed", "xpassed") for o in oeros):
        return KNOWN_GAP
    if all(o == "passed" for o in osrf + oeros):
        return PARITY
    return NOT_RUN  # skipped


def build(records: list[dict], specs: dict[str, specmod.Spec], matrix: matrixmod.Matrix):
    """Return (cells, details): cells[(spec, tier)] = state, details = per-criterion rows."""
    by_criterion: dict[tuple, dict[str, list[str]]] = defaultdict(lambda: {"osrf": [], "oeros": []})
    reasons: dict[tuple, list[str]] = defaultdict(list)
    both: dict[tuple[str, str], list[str]] = defaultdict(list)
    cross: dict[tuple, list[str]] = defaultdict(list)
    for rec in records:
        if rec.get("tier") is None:
            continue
        if rec.get("family") not in matrixmod.FAMILIES:
            # Tests that probe both families themselves (PS-013 inventories, PS-004 cross pairs).
            both[(rec["spec"], rec["tier"])].append(rec["outcome"])
            if rec.get("criterion"):
                cross[(rec["spec"], rec["tier"], rec["criterion"])].append(rec["outcome"])
            continue
        if not rec.get("criterion"):
            continue
        key = (rec["spec"], rec["tier"], rec["criterion"])
        by_criterion[key][rec["family"]].append(rec["outcome"])
        if rec.get("reason") and rec["family"] == "oeros":
            reasons[key].append(rec["reason"])

    criterion_states = {
        key: criterion_state(o["osrf"], o["oeros"]) for key, o in by_criterion.items()
    }
    for key, outcomes in cross.items():
        criterion_states[key] = cross_state(outcomes)

    cells: dict[tuple[str, str], str] = {}
    for spec in specs.values():
        applicable = set(spec.applicable_tiers(matrix))
        for tier in matrix.known_tiers:
            if tier not in applicable:
                cells[(spec.id, tier)] = NOT_APPLICABLE
                continue
            if spec.report_only:
                outcomes = both.get((spec.id, tier), [])
                if not outcomes:
                    cells[(spec.id, tier)] = NOT_RUN
                elif any(o in FAILING for o in outcomes):
                    cells[(spec.id, tier)] = NEW_GAP
                else:
                    cells[(spec.id, tier)] = REPORT_ONLY
                continue
            states = [
                s for (sid, t, _), s in criterion_states.items() if sid == spec.id and t == tier
            ]
            cells[(spec.id, tier)] = (
                next((s for s in SEVERITY if s in states), NOT_RUN) if states else NOT_RUN
            )

    details = [
        {
            "spec": sid,
            "tier": tier,
            "criterion": ac,
            "state": state,
            "reason": "; ".join(reasons[(sid, tier, ac)]),
        }
        for (sid, tier, ac), state in sorted(criterion_states.items())
        if state not in (PARITY, NOT_RUN)
    ]
    return cells, details


def _columns(cells: dict, matrix: matrixmod.Matrix) -> list[str]:
    return [
        t
        for t in matrix.known_tiers
        if any(s != NOT_APPLICABLE for (_, tier), s in cells.items() if tier == t)
    ]


def to_markdown(cells, details, specs, matrix, inventory=None) -> str:
    tiers = _columns(cells, matrix)
    lines = ["## Container parity matrix", ""]
    lines.append("| Spec | " + " | ".join(tiers) + " |")
    lines.append("| --- | " + " | ".join("---" for _ in tiers) + " |")
    for spec in specs.values():
        row = [
            "{} {}".format(*LABELS[cells[(spec.id, t)]])
            if cells[(spec.id, t)] != NOT_APPLICABLE
            else "—"
            for t in tiers
        ]
        lines.append(f"| {spec.id} {spec.title} | " + " | ".join(row) + " |")
    lines += ["", "Legend: " + ", ".join(f"{icon} {name}" for icon, name in LABELS.values()), ""]
    if details:
        lines += [
            "### Differences",
            "",
            "| Spec | Criterion | Tier | State | Note |",
            "| --- | --- | --- | --- | --- |",
        ]
        for d in details:
            icon, name = LABELS[d["state"]]
            lines.append(
                f"| {d['spec']} | {d['criterion']} | {d['tier']} | {icon} {name} | {d['reason']} |"
            )
        lines.append("")
    if inventory:
        lines += [
            "### Inventory differences (PS-013, report only)",
            "",
            "| Tier | Set | OSRF | oeros | Only OSRF | Only oeros | Intended |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
        for tier in matrix.known_tiers:
            for kind, d in (inventory.get(tier) or {}).items():
                lines.append(
                    f"| {tier} | {kind} | {d['osrf_count']} | {d['oeros_count']} "
                    f"| {len(d['only_osrf'])} | {len(d['only_oeros'])} | {len(d['intended'])} |"
                )
        lines.append("")
    return "\n".join(lines)


def to_html(cells, details, specs, matrix, inventory=None) -> str:
    tiers = _columns(cells, matrix)
    head = "".join(f"<th>{html.escape(t)}</th>" for t in tiers)
    rows = []
    for spec in specs.values():
        tds = []
        for t in tiers:
            state = cells[(spec.id, t)]
            icon, name = LABELS[state]
            tds.append(f'<td class="{state.replace("/", "")}" title="{name}">{icon} {name}</td>')
        rows.append(
            f"<tr><th>{html.escape(spec.id)} {html.escape(spec.title)}</th>{''.join(tds)}</tr>"
        )
    detail_rows = "".join(
        f"<tr><td>{d['spec']}</td><td>{d['criterion']}</td><td>{d['tier']}</td>"
        f"<td>{LABELS[d['state']][1]}</td><td>{html.escape(d['reason'])}</td></tr>"
        for d in details
    )
    inv_rows = "".join(
        f"<tr><td>{tier}</td><td>{kind}</td><td>{d['osrf_count']}</td><td>{d['oeros_count']}</td>"
        f'<td title="{html.escape(", ".join(d["only_osrf"]))}">{len(d["only_osrf"])}</td>'
        f'<td title="{html.escape(", ".join(d["only_oeros"]))}">{len(d["only_oeros"])}</td>'
        f"<td>{len(d['intended'])}</td></tr>"
        for tier in matrix.known_tiers
        for kind, d in ((inventory or {}).get(tier) or {}).items()
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Container parity matrix</title>
<style>
:root {{ color-scheme: light dark; font-family: system-ui, sans-serif; }}
table {{ border-collapse: collapse; margin: 1rem 0; }}
th, td {{ border: 1px solid #8886; padding: .35rem .6rem; text-align: left; }}
.parity {{ background: #2da44e33; }} .known-gap {{ background: #d4a72c44; }}
.new-gap {{ background: #cf222e44; }} .reference-broken {{ background: #82071e55; }}
.not-run, .na {{ opacity: .6; }} .report-only {{ background: #0969da22; }}
</style></head><body>
<h1>Container parity matrix</h1>
<table><thead><tr><th>Spec</th>{head}</tr></thead><tbody>{"".join(rows)}</tbody></table>
<h2>Differences</h2>
<table><thead><tr><th>Spec</th><th>Criterion</th><th>Tier</th><th>State</th><th>Note</th></tr></thead>
<tbody>{detail_rows}</tbody></table>
<h2>Inventory differences (PS-013, report only)</h2>
<table><thead><tr><th>Tier</th><th>Set</th><th>OSRF</th><th>oeros</th><th>Only OSRF</th><th>Only oeros</th><th>Intended</th></tr></thead>
<tbody>{inv_rows}</tbody></table>
</body></html>
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dirs", nargs="*", type=Path, default=[ROOT / "results" / "latest"])
    parser.add_argument("--out", type=Path, help="output directory (default: first results dir)")
    args = parser.parse_args(argv)

    records = load_records(args.dirs)
    if not records:
        print("parity_report: no results found", file=sys.stderr)
        return 1
    specs = specmod.load_all(ROOT / "specs")
    matrix = matrixmod.load(ROOT / "images.yaml")
    cells, details = build(records, specs, matrix)

    inventory = load_inventory(args.dirs)
    markdown = to_markdown(cells, details, specs, matrix, inventory)
    out = (args.out or args.dirs[0]).resolve()
    out.mkdir(parents=True, exist_ok=True)
    (out / "parity.md").write_text(markdown)
    (out / "parity.html").write_text(to_html(cells, details, specs, matrix, inventory))
    print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
