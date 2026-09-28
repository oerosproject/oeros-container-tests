"""Pin the OSRF reference images in images.yaml to their current multi-arch index digests.

    python -m tools.refresh_digests [--check]

Asks the Docker Hub registry API for each image's manifest digest, so it needs neither Docker
nor podman. Edits only the `digest` field of each one-line osrf entry, so comments and layout
survive. With --check it changes nothing and exits 1 if any digest is empty or stale.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IMAGES = ROOT / "images.yaml"

ENTRY = re.compile(
    r'(\{repo: (?P<repo>[^,]+), tag: (?P<tag>[^,]+), digest: ")(?P<digest>[^"]*)("\})'
)
ACCEPT = ", ".join(
    [
        "application/vnd.oci.image.index.v1+json",
        "application/vnd.docker.distribution.manifest.list.v2+json",
        "application/vnd.oci.image.manifest.v1+json",
        "application/vnd.docker.distribution.manifest.v2+json",
    ]
)


def current_digest(repo: str, tag: str) -> str:
    """Digest of the manifest (the index, for multi-arch images) that `repo:tag` points at."""
    repo = repo.removeprefix("docker.io/")
    if "/" not in repo:
        repo = f"library/{repo}"
    token_url = (
        f"https://auth.docker.io/token?service=registry.docker.io&scope=repository:{repo}:pull"
    )
    with urllib.request.urlopen(token_url, timeout=30) as resp:
        token = json.load(resp)["token"]
    request = urllib.request.Request(
        f"https://registry-1.docker.io/v2/{repo}/manifests/{tag}",
        method="HEAD",
        headers={"Authorization": f"Bearer {token}", "Accept": ACCEPT},
    )
    with urllib.request.urlopen(request, timeout=30) as resp:
        digest = resp.headers.get("Docker-Content-Digest", "")
    if not digest.startswith("sha256:"):
        raise RuntimeError(f"no digest returned for {repo}:{tag}")
    return digest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    text = IMAGES.read_text()
    stale: list[str] = []
    cache: dict[tuple[str, str], str] = {}

    def replace(match: re.Match) -> str:
        key = (match["repo"], match["tag"])
        if key not in cache:
            cache[key] = current_digest(*key)
        if match["digest"] != cache[key]:
            stale.append(f"{key[0]}:{key[1]} {match['digest'] or '(none)'} -> {cache[key]}")
        return f"{match.group(1)}{cache[key]}{match.group(5)}"

    try:
        updated = ENTRY.sub(replace, text)
    except (RuntimeError, OSError) as exc:
        print(f"refresh_digests: {exc}", file=sys.stderr)
        return 2

    for line in stale:
        print(line)
    if args.check:
        return 1 if stale else 0
    if updated != text:
        IMAGES.write_text(updated)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
