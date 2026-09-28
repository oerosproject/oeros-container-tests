"""Shell snippets and parsing helpers shared by the multi-step probe scripts.

The probes run as `sh -c` inside the images, so everything here is portable shell: the oeros
images use busybox utilities (no `timeout`, `head -n 3` and not `head -3`).
"""

from __future__ import annotations

import re
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent / "fixtures"

# Poll instead of sleeping for a fixed time: cold container starts can take many seconds on
# slow storage, and a fixed sleep makes timing-based checks flaky.
#   wait_for '<shell condition>' <seconds>
WAIT_FOR = """
wait_for() { n=0; while [ $n -lt "$2" ]; do sh -c "$1" >/dev/null 2>&1 && return 0; sleep 1; n=$((n+1)); done; return 1; }
"""

# Turtlesim and rqt need a Qt platform; `offscreen` needs no X server. PS-011 covers real Xvfb.
HEADLESS = "export QT_QPA_PLATFORM=offscreen\n"


def embed(container_path: str, fixture: str) -> str:
    """Shell that writes tests/fixtures/<fixture> to container_path."""
    body = (FIXTURES / fixture).read_text()
    return f"cat > {container_path} <<'OEROS_FIXTURE_EOF'\n{body}\nOEROS_FIXTURE_EOF\n"


def sections(stdout: str) -> dict[str, str]:
    """Split output on `##NAME` marker lines into {NAME: text}."""
    parts = re.split(r"^##(\w+)\n", stdout, flags=re.MULTILINE)
    return dict(zip(parts[1::2], parts[2::2], strict=False))


def exit_ok(section: str) -> bool:
    """True if the section has an `exit=0` line (print `exit=$rc` right after the command)."""
    return re.search(r"^exit=0$", section, flags=re.MULTILINE) is not None


def pose(section: str) -> dict[str, float]:
    """Parse `x: 1.0` style lines from `ros2 topic echo` output."""
    return {k: float(v) for k, v in re.findall(r"^(x|y|theta): (-?[\d.e+-]+)$", section, re.M)}
