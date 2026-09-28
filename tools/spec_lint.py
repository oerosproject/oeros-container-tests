"""spec-lint: static checks that need no Docker.

* every spec has valid front matter and a known status
* a spec at Approved or later has a test for every acceptance criterion
* every `@pytest.mark.spec(...)` names a known spec and criterion
* images.yaml, gaps.yaml, contracts/ and compose/ parse as YAML
* gaps.yaml entries point at real specs and criteria
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import yaml

from tools import specs as specmod

ROOT = Path(__file__).resolve().parent.parent


def _is_spec_marker(node: ast.expr) -> bool:
    """Match `pytest.mark.spec(...)`."""
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "spec"
        and isinstance(node.func.value, ast.Attribute)
        and node.func.value.attr == "mark"
    )


def traced_criteria(test_dir: Path) -> tuple[dict[tuple[str, str], list[str]], list[str]]:
    """Return ({(spec, criterion): [test files]}, [errors]) by scanning test sources."""
    traced: dict[tuple[str, str], list[str]] = {}
    errors: list[str] = []
    for path in sorted(test_dir.rglob("test_*.py")):
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if not _is_spec_marker(node):
                continue
            args = [a.value for a in node.args if isinstance(a, ast.Constant)]
            where = f"{path.relative_to(ROOT)}:{node.lineno}"
            if len(args) != len(node.args) or len(args) < 2:
                errors.append(
                    f"{where}: spec marker needs a spec id and criteria as string literals"
                )
                continue
            for criterion in args[1:]:
                traced.setdefault((args[0], criterion), []).append(where)
    return traced, errors


def lint(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    try:
        specs = specmod.load_all(root / "specs")
    except specmod.SpecError as exc:
        return [str(exc)]

    for spec in specs.values():
        if spec.status not in specmod.STATUSES:
            errors.append(f"{spec.path.name}: unknown status {spec.status!r}")
        if not spec.criteria:
            errors.append(f"{spec.path.name}: no acceptance criteria (lines like 'AC1: ...')")

    traced, marker_errors = traced_criteria(root / "tests")
    errors += marker_errors
    for (spec_id, criterion), where in sorted(traced.items()):
        if spec_id not in specs:
            errors.append(f"{where[0]}: unknown spec {spec_id}")
        elif criterion not in specs[spec_id].criteria:
            errors.append(f"{where[0]}: {spec_id} has no criterion {criterion}")

    for spec in specs.values():
        if spec.status in specmod.TRACED_STATUSES:
            for criterion in spec.criteria:
                if (spec.id, criterion) not in traced:
                    errors.append(f"{spec.path.name}: {spec.status} but {criterion} has no test")
            if not spec.source_sha:
                errors.append(f"{spec.path.name}: {spec.status} but source_sha is not pinned")

    errors += _lint_yaml(root, specs)
    return errors


def _lint_yaml(root: Path, specs: dict[str, specmod.Spec]) -> list[str]:
    errors: list[str] = []
    files = [root / "images.yaml", root / "gaps.yaml"]
    for pattern in ("contracts/*.yaml", "compose/*.yaml"):
        files += sorted(root.glob(pattern))
    for path in files:
        try:
            data = yaml.safe_load(path.read_text())
        except (OSError, yaml.YAMLError) as exc:
            errors.append(f"{path.relative_to(root)}: {exc}")
            continue
        if path.name == "gaps.yaml":
            for gap in (data or {}).get("gaps") or []:
                spec = specs.get(gap.get("spec"))
                if spec is None or gap.get("criterion") not in spec.criteria:
                    errors.append(f"gaps.yaml: {gap.get('spec')}/{gap.get('criterion')} is unknown")
                if not gap.get("issue"):
                    errors.append(
                        f"gaps.yaml: {gap.get('spec')}/{gap.get('criterion')} has no issue"
                    )
    return errors


def main() -> int:
    errors = lint()
    for error in errors:
        print(f"spec-lint: {error}", file=sys.stderr)
    if not errors:
        print("spec-lint: ok")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
