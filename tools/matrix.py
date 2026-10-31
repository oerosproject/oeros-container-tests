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
FAMILIES = ("osrf", "oeros", "sloretz")
# Pulled from another publisher and pinned by digest, like the OSRF reference.
EXTERNAL_FAMILIES = ("osrf", "sloretz")
# Their failures are recorded as differences and do not fail the run (they are not ours to fix).
REPORT_ONLY_FAMILIES = ("sloretz",)
# When the key has no image for a tier/arch (images.yaml `<family>_arches`), the value stands
# in as the required reference instead (reference_family()). A permanent gap, not flakiness:
# see the images.yaml note by `osrf_arches`.
REFERENCE_FALLBACK = {"osrf": "sloretz"}
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

    def families(self, tier: str, arch: str | None = None) -> list[str]:
        """The families that publish an image for `tier` (sloretz has no dev image).

        With `arch`, drop a family that does not publish for it (images.yaml `<family>_arches`),
        for example osrf on arm64 for the desktop tiers.
        """
        names = [f for f in FAMILIES if f in self.entry(tier)]
        if arch is None:
            return names
        return [f for f in names if arch in self.family_arches(tier, f)]

    def arches(self, tier: str) -> list[str]:
        """Architectures the oeros image of `tier` is published for (images.yaml `arches`)."""
        return self.family_arches(tier, "oeros")

    def family_arches(self, tier: str, family: str) -> list[str]:
        """Architectures `family` is published for, for `tier`; default is both.

        oeros keeps this inside its own mapping (`arches:`); osrf and sloretz are one-line
        dicts tools/refresh_digests.py rewrites in place, so theirs is a sibling
        `<family>_arches` key instead, to keep that dict's shape exactly `{repo, tag, digest}`.
        """
        entry = self.entry(tier)
        if family == "oeros":
            return list(entry["oeros"].get("arches", ARCHES))
        return list(entry.get(f"{family}_arches", ARCHES))

    def reference_family(self, tier: str, arch: str) -> str:
        """The external family that must pass for `tier`/`arch`.

        Normally osrf; falls back along REFERENCE_FALLBACK (currently just osrf -> sloretz)
        when osrf has no image for that arch.
        """
        family = "osrf"
        seen = {family}
        while arch not in self.family_arches(tier, family):
            family = REFERENCE_FALLBACK.get(family)
            if family is None or family in seen or family not in self.families(tier):
                raise MatrixError(f"no reference family publishes {tier!r} for arch {arch!r}")
            seen.add(family)
        return family

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
    if family not in matrix.families(tier):
        raise MatrixError(f"{family} publishes no image for tier {tier!r}")
    entry = matrix.entry(tier)[family]
    if family in EXTERNAL_FAMILIES:
        digest = entry.get("digest") or ""
        if digest:
            return f"{entry['repo']}@{digest}"
        if env.get("REQUIRE_PINNED_DIGESTS") == "1":
            raise MatrixError(
                f"{family} {tier} ({entry['repo']}:{entry['tag']}) has no digest and "
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
    # "all" is the six REP-2001 tiers plus the extra ones (dev), so PS-005 runs in CI too.
    tier_list = (
        matrix.known_tiers if tiers.strip() in ("", "all") else tiers.replace(",", " ").split()
    )
    arch_list = list(ARCHES) if arches.strip() == "all" else arches.replace(",", " ").split()
    for tier in tier_list:
        matrix.entry(tier)
    for arch in arch_list:
        if arch not in ARCHES:
            raise MatrixError(f"unknown arch {arch!r}; known: {', '.join(ARCHES)}")
    # Skip a tier on an architecture its oeros image is not published for.
    include = [
        {"tier": t, "arch": a} for t in tier_list for a in arch_list if a in matrix.arches(t)
    ]
    if not include:
        raise MatrixError(
            f"nothing to test: none of the tiers {tier_list} is published for {arch_list}"
        )
    return {"include": include}


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
                for family in matrix.families(tier, args.arch):
                    ref = image_ref(matrix, family, tier, arch=args.arch)
                    print(f"{tier:13} {family:6} {ref}")
    except MatrixError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
