"""Run tests inside a throwaway Docker container.

We never exec AI-generated code on the host — that is the whole safety pitch.
"""

from __future__ import annotations

import io
import tarfile
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

import docker
from docker.errors import DockerException, ImageNotFound


LogCallback = Callable[[str], None]


@dataclass
class SandboxResult:
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int


def _ensure_image(client: docker.DockerClient, image: str, on_log: LogCallback | None) -> None:
    try:
        client.images.get(image)
        return
    except ImageNotFound:
        pass

    backend = Path(__file__).resolve().parents[2]
    local_map = {
        "autopatch-sandbox:latest": backend / "sandbox",
        "autopatch-node-sandbox:latest": backend / "sandbox-node",
    }
    local_dir = local_map.get(image)
    if local_dir and (local_dir / "Dockerfile").exists():
        if on_log:
            on_log(f"$ docker build -t {image}\n")
        client.images.build(path=str(local_dir), tag=image, rm=True)
        return

    if on_log:
        on_log(f"$ docker pull {image}\n")
    for line in client.api.pull(image, stream=True, decode=True):
        status = line.get("status", "")
        detail = line.get("id", "")
        if on_log and status:
            on_log(f"{status} {detail}\n".rstrip() + "\n")


def _pack_workspace(workspace: Path) -> bytes:
    buf = io.BytesIO()
    skip_dirs = {".git", "node_modules", "dist", ".next", "coverage", "__pycache__"}
    with tarfile.open(fileobj=buf, mode="w") as tar:
        for path in workspace.rglob("*"):
            if any(part in skip_dirs for part in path.parts):
                continue
            if path.is_file():
                tar.add(path, arcname=path.relative_to(workspace).as_posix())
    buf.seek(0)
    return buf.read()


def run_command_sandbox(
    workspace: Path,
    command: Sequence[str],
    *,
    image: str,
    timeout_sec: int = 90,
    mem_limit: str = "512m",
    nano_cpus: int = 1_000_000_000,
    on_log: LogCallback | None = None,
    log_label: str | None = None,
) -> SandboxResult:
    """Overlay workspace into an ephemeral container and run `command` with no network."""
    started = time.perf_counter()
    client = docker.from_env()
    _ensure_image(client, image, on_log)

    container = client.containers.create(
        image=image,
        command=list(command),
        working_dir="/workspace",
        network_disabled=True,
        mem_limit=mem_limit,
        nano_cpus=nano_cpus,
        auto_remove=False,
        detach=True,
    )

    try:
        archive = _pack_workspace(workspace)
        container.put_archive("/workspace", archive)

        if on_log:
            on_log(f"$ {log_label or ' '.join(command)}\n")

        container.start()

        deadline = time.time() + timeout_sec
        log_cursor = 0
        while True:
            container.reload()
            raw = container.logs(stdout=True, stderr=True)
            text = raw.decode("utf-8", errors="replace")
            if on_log and len(text) > log_cursor:
                on_log(text[log_cursor:])
                log_cursor = len(text)

            if container.status not in ("created", "running"):
                break
            if time.time() >= deadline:
                container.kill()
                if on_log:
                    on_log("\n[sandbox] killed — exceeded timeout\n")
                break
            time.sleep(0.25)

        raw = container.logs(stdout=True, stderr=True)
        full = raw.decode("utf-8", errors="replace")
        if on_log and len(full) > log_cursor:
            on_log(full[log_cursor:])

        state = container.wait(timeout=10)
        exit_code = int(state.get("StatusCode", 1))
        duration_ms = int((time.perf_counter() - started) * 1000)
        return SandboxResult(
            exit_code=exit_code,
            stdout=full,
            stderr="",
            duration_ms=duration_ms,
        )
    except DockerException as exc:
        if on_log:
            on_log(f"[sandbox] docker error: {exc}\n")
        duration_ms = int((time.perf_counter() - started) * 1000)
        return SandboxResult(exit_code=1, stdout="", stderr=str(exc), duration_ms=duration_ms)
    finally:
        try:
            container.remove(force=True)
        except Exception:
            pass


def run_pytest_sandbox(
    workspace: Path,
    *,
    image: str = "autopatch-sandbox:latest",
    timeout_sec: int = 60,
    mem_limit: str = "256m",
    nano_cpus: int = 1_000_000_000,
    on_log: LogCallback | None = None,
) -> SandboxResult:
    cmd: list[str] = ["python", "-m", "pytest", "-q", "--tb=short"]
    if image.startswith("python:"):
        cmd = [
            "bash",
            "-lc",
            "pip install -q pytest && python -m pytest -q --tb=short",
        ]
    return run_command_sandbox(
        workspace,
        cmd,
        image=image,
        timeout_sec=timeout_sec,
        mem_limit=mem_limit,
        nano_cpus=nano_cpus,
        on_log=on_log,
        log_label="pytest -q --tb=short",
    )


def run_node_sandbox(
    workspace: Path,
    command: Sequence[str] | None = None,
    *,
    image: str = "autopatch-node-sandbox:latest",
    timeout_sec: int = 120,
    mem_limit: str = "768m",
    on_log: LogCallback | None = None,
) -> SandboxResult:
    cmd = list(command or ["npm", "test"])
    return run_command_sandbox(
        workspace,
        cmd,
        image=image,
        timeout_sec=timeout_sec,
        mem_limit=mem_limit,
        on_log=on_log,
        log_label=" ".join(cmd),
    )
