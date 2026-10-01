"""Image matrix: load images.yaml and resolve image references.

Used by the pytest fixtures and by the `resolve` CI job (`python -m tools.matrix github-matrix`).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
FAMILIES = ("osrf", "oeros")
ARCHES = ("amd64", "arm64")


def oeros_name(entry: dict, tag: str, arch: str) -> str:
    """`<namespace><repository>:<tag>-<arch>` for one oeros image, with no registry prefix.

    `entry` is the tier's `oeros` mapping from images.yaml. The arch-specific tag is the one
    meta-oeros publishes for each architecture, and the name a local load gives the image
    (the build records it next to the OCI layout in <recipe>-oci.publish).
    """
    if arch not in ARCHES:
        raise MatrixError(f"unknown arch {arch!r} for an oeros image; known: {', '.join(ARCHES)}")
    return f"{entry.get('namespace', '')}{entry['repository']}:{tag}-{arch}"


class MatrixError(Exception):
    pass


@dataclass(frozen=True)
class Matrix:
    defaults: dict
    tiers: dict  # the six REP-2001 tiers, in order
    extra_tiers: dict  # e.g. dev

    @property
    def all_tiers(self) -> list[str]:
        return list(self.tiers)

    @property
    def known_tiers(self) -> list[str]:
        return [*self.tiers, *self.extra_tiers]

    def entry(self, tier: str) -> dict:
        try:
            return {**self.tiers, **self.extra_tiers}[tier]
        except KeyError:
            raise MatrixError(
                f"unknown tier {tier!r}; known: {', '.join(self.known_tiers)}"
            ) from None


def load(path: Path = ROOT / "images.yaml") -> Matrix:
    data = yaml.safe_load(path.read_text())
    return Matrix(
        defaults=data["defaults"],
        tiers=data["tiers"],
        extra_tiers=data.get("extra_tiers") or {},
    )


def image_ref(
    matrix: Matrix, family: str, tier: str, env: dict | None = None, arch: str | None = None
) -> str:
    """Return the pullable reference for one cell of the matrix."""
    env = os.environ if env is None else env
    entry = matrix.entry(tier)[family]
    if family == "osrf":
        digest = entry.get("digest") or ""
        if digest:
            return f"{entry['repo']}@{digest}"
        if env.get("REQUIRE_PINNED_DIGESTS") == "1":
            raise MatrixError(
                f"osrf {tier} ({entry['repo']}:{entry['tag']}) has no digest and "
                "REQUIRE_PINNED_DIGESTS=1; run the refresh-digests workflow"
            )
        return f"{entry['repo']}:{entry['tag']}"
    tag = env.get("OEROS_TAG") or matrix.defaults["oeros_tag"]
    name = oeros_name(entry, tag, arch or "amd64")
    if env.get("OEROS_SOURCE", "registry") == "local":
        return name
    registry = env.get("OEROS_REGISTRY") or matrix.defaults["oeros_registry"]
    return f"{registry}/{name}"


def _github_matrix(matrix: Matrix, tiers: str, arches: str) -> dict:
    tier_list = (
        matrix.all_tiers if tiers.strip() in ("", "all") else tiers.replace(",", " ").split()
    )
    arch_list = list(ARCHES) if arches.strip() == "all" else arches.replace(",", " ").split()
    for tier in tier_list:
        matrix.entry(tier)
    for arch in arch_list:
        if arch not in ARCHES:
            raise MatrixError(f"unknown arch {arch!r}; known: {', '.join(ARCHES)}")
    return {"include": [{"tier": t, "arch": a} for t in tier_list for a in arch_list]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    gh = sub.add_parser("github-matrix", help="print the strategy.matrix JSON")
    gh.add_argument("--tiers", default="all", help="'all' or space/comma separated tiers")
    gh.add_argument("--arches", default="amd64", help="'all' or space/comma separated arches")
    refs = sub.add_parser("refs", help="print every image reference")
    refs.add_argument("--tier", action="append")
    refs.add_argument("--arch", default="amd64", choices=ARCHES)
    args = parser.parse_args(argv)

    matrix = load()
    try:
        if args.cmd == "github-matrix":
            print(json.dumps(_github_matrix(matrix, args.tiers, args.arches)))
        else:
            for tier in args.tier or matrix.known_tiers:
                for family in FAMILIES:
                    ref = image_ref(matrix, family, tier, arch=args.arch)
                    print(f"{tier:13} {family:6} {ref}")
    except MatrixError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
