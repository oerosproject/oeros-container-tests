"""Load locally built oeros images from a bitbake deploy directory into the container store.

    python -m tools.load_oeros [--tier ros-core ...] [--arch amd64] [--mc oeros-x86-64]

Each image is stored as `<image>:<tag>-<arch>` (the name OEROS_SOURCE=local expects), for
example `oeros-container-ros-core:lyrical-wrynose-amd64`. Images whose ID already matches the
OCI layout are skipped. Uses `oci:` layouts directly, so no skopeo is needed.

Environment: OEROS_BUILD_DIR (bitbake build dir), OEROS_TAG, CONTAINER_RUNTIME.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from tests.runtime import Runtime
from tools import matrix as matrixmod

DEFAULT_BUILD_DIR = "/opt/yocto/meta-oeros/bitbake-builds/oeros-wrynose-lyrical/build"
# arch -> (default multiconfig, machine)
TARGETS = {
    "amd64": ("oeros-x86-64", "genericx86-64"),
    "arm64": ("oeros-arm64", "genericarm64"),
}


def layout_dir(build_dir: Path, mc: str, machine: str, image: str) -> Path:
    return build_dir / f"tmp-{mc}" / "deploy" / "images" / machine / f"{image}-latest-oci"


def layout_image_id(layout: Path) -> str:
    """The image ID of an OCI layout is its config digest."""
    index = json.loads((layout / "index.json").read_text())
    manifest_digest = index["manifests"][0]["digest"].split(":")[1]
    manifest = json.loads((layout / "blobs" / "sha256" / manifest_digest).read_text())
    return manifest["config"]["digest"].split(":")[1]


def _run(argv: list[str], env: dict[str, str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(argv, capture_output=True, text=True, check=True, env=env, **kwargs)


def load_layout(runtime: Runtime, layout: Path, ref: str) -> None:
    binary = runtime.binary
    if os.path.basename(binary) == "podman":
        image_id = _run(
            [binary, "pull", "-q", f"oci:{layout.resolve()}:latest"], runtime.env
        ).stdout
        image_id = image_id.strip().splitlines()[-1]
        _run([binary, "tag", image_id, ref], runtime.env)
        # `oci:...:latest` also leaves a stray docker.io/library/latest:latest name behind.
        subprocess.run(
            [binary, "untag", image_id, "docker.io/library/latest:latest"],
            capture_output=True,
            check=False,
            env=runtime.env,
        )
    else:
        tar = subprocess.Popen(
            ["tar", "-C", str(layout.resolve()), "-c", "."], stdout=subprocess.PIPE
        )
        loaded = subprocess.run(
            [binary, "load", "-q"], stdin=tar.stdout, capture_output=True, text=True, check=True
        )
        tar.wait()
        image_id = loaded.stdout.strip().rsplit(" ", 1)[-1]
        _run([binary, "tag", image_id, ref], runtime.env)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tier", action="append", help="tier to load (default: all six)")
    parser.add_argument("--arch", default="amd64", choices=list(TARGETS))
    parser.add_argument("--mc", help="multiconfig (default: oeros-x86-64 or oeros-arm64)")
    parser.add_argument("--build-dir", default=os.environ.get("OEROS_BUILD_DIR", DEFAULT_BUILD_DIR))
    args = parser.parse_args(argv)

    matrix = matrixmod.load()
    default_mc, machine = TARGETS[args.arch]
    mc = args.mc or default_mc
    runtime = Runtime()
    env = {**os.environ, "OEROS_SOURCE": "local"}
    status = 0
    for tier in args.tier or matrix.all_tiers:
        image = matrix.entry(tier)["oeros"]["image"]
        ref = matrixmod.image_ref(matrix, "oeros", tier, env=env, arch=args.arch)
        layout = layout_dir(Path(args.build_dir), mc, machine, image)
        if not (layout / "index.json").exists():
            print(f"{tier:13} missing  {layout}", file=sys.stderr)
            status = 1
            continue
        current = subprocess.run(
            [runtime.binary, "image", "inspect", "--format", "{{.Id}}", ref],
            capture_output=True,
            text=True,
            check=False,
        )
        if current.returncode == 0 and current.stdout.strip().removeprefix(
            "sha256:"
        ) == layout_image_id(layout):
            print(f"{tier:13} current  {ref}")
            continue
        load_layout(runtime, layout, ref)
        print(f"{tier:13} loaded   {ref}")
    return status


if __name__ == "__main__":
    raise SystemExit(main())
