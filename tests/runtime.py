"""Thin wrapper over the container runtime CLI.

Probes run through the image's own entrypoint, never a hard-coded shell, because the oeros
base is busybox. The runtime binary is a variable so podman can be added later without
touching the specs.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import uuid
from dataclasses import dataclass

TIMED_OUT = 124


@dataclass
class ProbeResult:
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool = False

    @property
    def ok(self) -> bool:
        return self.exit_code == 0

    @property
    def output(self) -> str:
        return self.stdout + self.stderr


def detect_runtime() -> str:
    """CONTAINER_RUNTIME if set, else docker when its daemon is reachable, else podman."""
    if os.environ.get("CONTAINER_RUNTIME"):
        return os.environ["CONTAINER_RUNTIME"]
    if shutil.which("docker"):
        probe = subprocess.run(["docker", "version"], capture_output=True, check=False)
        if probe.returncode == 0:
            return "docker"
    return "podman" if shutil.which("podman") else "docker"


class Runtime:
    def __init__(self, binary: str | None = None):
        self.binary = binary or detect_runtime()
        self.env = _registry_env()

    def has_image(self, ref: str) -> bool:
        proc = subprocess.run(
            [self.binary, "image", "inspect", ref], capture_output=True, check=False
        )
        return proc.returncode == 0

    def image_config(self, ref: str) -> dict:
        """Normalized image config: entrypoint, cmd, user, workdir, env (dict)."""
        proc = subprocess.run(
            [self.binary, "image", "inspect", "--format", "{{json .Config}}", ref],
            capture_output=True,
            text=True,
            check=True,
        )
        raw = json.loads(proc.stdout)
        env = dict(item.split("=", 1) for item in raw.get("Env") or [])
        return {
            "entrypoint": raw.get("Entrypoint") or [],
            "cmd": raw.get("Cmd") or [],
            "user": raw.get("User") or "",
            "workdir": raw.get("WorkingDir") or "",
            "env": env,
        }

    def pull(self, ref: str, platform: str) -> ProbeResult:
        return self._exec([self.binary, "pull", "--platform", platform, ref], timeout=1800)

    def run(
        self,
        ref: str,
        cmd: list[str],
        *,
        platform: str,
        env: dict[str, str] | None = None,
        entrypoint: str | None = None,
        volumes: list[str] | None = None,
        timeout: float = 60,
    ) -> ProbeResult:
        name = f"oeros-probe-{uuid.uuid4().hex[:12]}"
        argv = [self.binary, "run", "--rm", "--name", name, "--platform", platform]
        for key, value in (env or {}).items():
            argv += ["-e", f"{key}={value}"]
        for volume in volumes or []:
            argv += ["-v", volume]
        if entrypoint is not None:
            argv += ["--entrypoint", entrypoint]
        argv += [ref, *cmd]
        result = self._exec(argv, timeout=timeout)
        if result.timed_out:
            subprocess.run([self.binary, "kill", name], capture_output=True, check=False)
        return result

    # -- long-running containers: sidecars, multi-container scenarios ---------------------------

    def network_create(self, name: str) -> None:
        self._check([self.binary, "network", "create", name])

    def network_rm(self, name: str) -> None:
        self._exec([self.binary, "network", "rm", "-f", name], timeout=60)

    def volume_create(self, name: str) -> None:
        self._check([self.binary, "volume", "create", name])

    def volume_rm(self, name: str) -> None:
        self._exec([self.binary, "volume", "rm", "-f", name], timeout=60)

    def build(self, tag: str, context: str) -> None:
        self._check([self.binary, "build", "-t", tag, context], timeout=1800)

    def start(
        self,
        ref: str,
        cmd: list[str],
        *,
        name: str,
        platform: str | None = None,
        network: str | None = None,
        env: dict[str, str] | None = None,
        volumes: list[str] | None = None,
    ) -> None:
        """Start a detached container (removed by `remove`)."""
        argv = [self.binary, "run", "-d", "--name", name]
        if platform:
            argv += ["--platform", platform]
        if network:
            argv += ["--network", network]
        for key, value in (env or {}).items():
            argv += ["-e", f"{key}={value}"]
        for volume in volumes or []:
            argv += ["-v", volume]
        self._check([*argv, ref, *cmd])

    def logs(self, name: str) -> str:
        return self._exec([self.binary, "logs", name], timeout=60).output

    def exec(self, name: str, cmd: list[str], timeout: float = 60) -> ProbeResult:
        return self._exec([self.binary, "exec", name, *cmd], timeout=timeout)

    def is_running(self, name: str) -> bool:
        result = self._exec([self.binary, "inspect", "--format", "{{.State.Running}}", name], 30)
        return result.stdout.strip() == "true"

    def remove(self, *names: str) -> None:
        for name in names:
            self._exec([self.binary, "rm", "-f", name], timeout=60)

    def compose_command(self) -> list[str] | None:
        """The compose provider to use, or None when there is none (`<runtime> compose`)."""
        for candidate in ([self.binary, "compose"], ["podman-compose"], ["docker-compose"]):
            if shutil.which(candidate[0]) and (
                len(candidate) == 1
                or self._exec([*candidate, "version"], timeout=30).exit_code == 0
            ):
                return candidate
        return None

    def _check(self, argv: list[str], timeout: float = 120) -> ProbeResult:
        result = self._exec(argv, timeout=timeout)
        if not result.ok:
            raise RuntimeError(f"{' '.join(argv)} failed ({result.exit_code}):\n{result.output}")
        return result

    def _exec(self, argv: list[str], timeout: float) -> ProbeResult:
        return self.exec_env(argv, self.env, timeout)

    @staticmethod
    def exec_env(argv: list[str], env: dict[str, str], timeout: float) -> ProbeResult:
        try:
            proc = subprocess.run(
                argv, capture_output=True, text=True, timeout=timeout, check=False, env=env
            )
        except subprocess.TimeoutExpired as exc:
            return ProbeResult(TIMED_OUT, _text(exc.stdout), _text(exc.stderr), timed_out=True)
        return ProbeResult(proc.returncode, proc.stdout, proc.stderr)


def _registry_env() -> dict[str, str]:
    """Environment for the runtime CLI.

    podman reads ~/.docker/config.json for registry credentials and fails outright when the
    file exists but is not readable. Point it at an empty auth file instead, which is enough
    for the anonymous pulls of public images this suite does.
    """
    env = dict(os.environ)
    config = os.path.join(env.get("DOCKER_CONFIG", os.path.expanduser("~/.docker")), "config.json")
    if (
        "REGISTRY_AUTH_FILE" not in env
        and os.path.exists(config)
        and not os.access(config, os.R_OK)
    ):
        empty = os.path.join(tempfile.gettempdir(), f"oeros-tests-auth-{os.getuid()}.json")
        with open(empty, "w") as fh:
            fh.write("{}")
        env["REGISTRY_AUTH_FILE"] = empty
    return env


def _text(value: bytes | str | None) -> str:
    if value is None:
        return ""
    return value.decode(errors="replace") if isinstance(value, bytes) else value
