"""Command-line options, loaded early with `-p` (see pyproject.toml).

They live in a plugin rather than tests/conftest.py because pytest parses the command line
before it reads that conftest, and mistakes `--results-dir <existing dir>` for a test path.
"""

from __future__ import annotations

import platform as host_platform
import time
from pathlib import Path

import pytest

from tests.plugins.spec_trace import ARCH, RESULTS_DIR
from tools import matrix as matrixmod

ROOT = Path(__file__).resolve().parent.parent.parent
FAMILIES = matrixmod.FAMILIES


def _host_arch() -> str:
    return {"x86_64": "amd64", "aarch64": "arm64", "arm64": "arm64"}.get(
        host_platform.machine(), "amd64"
    )


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("oeros", "oeros container parity")
    group.addoption("--tier", action="append", help="run only this tier (repeatable)")
    group.addoption(
        "--family", action="append", choices=FAMILIES, help="run only this family (repeatable)"
    )
    group.addoption("--spec", action="append", help="run only this spec, e.g. PS-004 (repeatable)")
    group.addoption("--arch", default=_host_arch(), choices=matrixmod.ARCHES)
    group.addoption("--run-id", default=time.strftime("%Y%m%d-%H%M%S"))
    group.addoption(
        "--record-commands",
        action="store_true",
        help="write the runtime commands each test issues to <results>/commands.json",
    )
    group.addoption("--results-dir", default="results", help="parent of results/<run-id>/")


def pytest_configure(config: pytest.Config) -> None:
    results = Path(config.getoption("--results-dir"))
    if not results.is_absolute():
        results = ROOT / results
    config.stash[RESULTS_DIR] = results / config.getoption("--run-id")
    config.stash[ARCH] = config.getoption("--arch")
