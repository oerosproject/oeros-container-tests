"""Named local sessions. Each one calls the same pytest command CI uses.

    nox -s smoke
    nox -s parity -- --tier desktop
    nox -s parity -- --spec PS-004 -x

Everything after `--` is passed to pytest. Results land in results/<run-id>/.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import nox

nox.options.default_venv_backend = "uv|virtualenv"
nox.options.sessions = ["lint", "smoke"]

RESULTS = Path("results")


def _install(session: nox.Session) -> None:
    session.install("-e", ".[dev,podman]")


def _pytest(session: nox.Session, *args: str, env: dict[str, str] | None = None) -> None:
    """Run pytest with the JUnit and Allure outputs CI publishes."""
    run_id = os.environ.get("RUN_ID") or time.strftime("%Y%m%d-%H%M%S")
    out = RESULTS / run_id
    session.run(
        "pytest",
        "--run-id",
        run_id,
        f"--junitxml={out}/junit.xml",
        f"--alluredir={out}/allure-results",
        *args,
        *session.posargs,
        env=env,
    )


@nox.session
def smoke(session: nox.Session) -> None:
    """PS-001, PS-002, PS-012 on ros-core and ros-base, host architecture."""
    _install(session)
    _pytest(
        session,
        "-m",
        "not slow and not gui",
        "--spec",
        "PS-001",
        "--spec",
        "PS-002",
        "--spec",
        "PS-012",
        "--tier",
        "ros-core",
        "--tier",
        "ros-base",
    )


@nox.session
def parity(session: nox.Session) -> None:
    """Every spec for the tiers you pass, both families. Example: -- --tier desktop"""
    _install(session)
    _pytest(session)


@nox.session
def gui(session: nox.Session) -> None:
    """PS-011 with the Xvfb sidecar."""
    _install(session)
    _pytest(session, "-m", "gui", "--spec", "PS-011")


@nox.session
def arm64(session: nox.Session) -> None:
    """Same specs under QEMU emulation; spot checks only. Example: -- --tier ros-base"""
    _install(session)
    session.log(
        "needs QEMU binfmt handlers: docker run --privileged --rm tonistiigi/binfmt --install arm64"
    )
    _pytest(session, "--arch", "arm64")


@nox.session
def ci(session: nox.Session) -> None:
    """The invocation GitHub Actions uses: strict, pinned reference images."""
    _install(session)
    _pytest(session, env={"REQUIRE_PINNED_DIGESTS": os.environ.get("REQUIRE_PINNED_DIGESTS", "1")})


@nox.session
def report(session: nox.Session) -> None:
    """Build the parity matrix from the last run (or the results dirs you pass)."""
    _install(session)
    dirs = session.posargs or [str(RESULTS / "latest")]
    session.run("python", "-m", "tools.parity_report", *dirs)


@nox.session
def lint(session: nox.Session) -> None:
    """spec-lint, ruff, YAML validation."""
    _install(session)
    session.run("python", "-m", "tools.spec_lint")
    session.run("ruff", "check", ".")
    session.run("ruff", "format", "--check", ".")
