"""LangGraph node functions — each one does one job and emits UI events."""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any, Callable

from app.graph.state import PatchState
from app.services.diff_utils import unified_diff
from app.services.fixtures import get_spec, materialize_workspace
from app.services.gemini import generate_patch
from app.services.git_commit import commit_patch
from app.services.github_pr import try_open_pull_request
from app.tools.docker_sandbox import run_node_sandbox, run_pytest_sandbox

EmitFn = Callable[[dict[str, Any]], None]


def _emit(state: PatchState, emit: EmitFn | None, event_type: str, **payload: Any) -> None:
    event = {
        "type": event_type,
        "run_id": state.get("run_id"),
        "ts": time.time(),
        "iteration": state.get("iteration", 0),
        "active_node": state.get("active_node"),
        **payload,
    }
    events = list(state.get("events") or [])
    events.append(event)
    state["events"] = events
    if emit:
        emit(event)


def ingest_node(state: PatchState, emit: EmitFn | None = None) -> PatchState:
    state["active_node"] = "ingest"
    state["status"] = "running"
    state["iteration"] = 0
    state["started_at"] = time.time()

    spec = get_spec(state["fixture_id"])
    state["runtime"] = spec.runtime
    state["language"] = spec.language
    state["source_file"] = spec.source_file
    state["test_file"] = spec.test_file
    state["test_command"] = list(spec.test_command)

    workspace = Path(state["workspace"])
    materialize_workspace(spec, workspace)

    source = (workspace / spec.source_file).read_text(encoding="utf-8")
    tests = (
        (workspace / spec.test_file).read_text(encoding="utf-8")
        if spec.test_file and (workspace / spec.test_file).exists()
        else state.get("test_code", "")
    )
    state["source_code"] = source
    state["test_code"] = tests
    state["original_source"] = source
    state["patched_source"] = source
    if state.get("seed_error_log"):
        state["error_log"] = state["seed_error_log"]

    _emit(
        state,
        emit,
        "node",
        message=f"Ingested {spec.runtime} project · scoped file {spec.source_file}",
        status=state["status"],
        source_code=source,
        test_code=tests,
        original_source=source,
        patched_source=source,
        runtime=spec.runtime,
        source_file=spec.source_file,
    )
    return state


def generate_patch_node(state: PatchState, emit: EmitFn | None = None) -> PatchState:
    state["active_node"] = "generate_patch"
    state["iteration"] = int(state.get("iteration", 0)) + 1
    source_file = state.get("source_file", "impl.py")
    language = state.get("language", "python")

    _emit(
        state,
        emit,
        "node",
        message=f"Gemini analyzing failure (attempt {state['iteration']}/{state.get('max_iterations', 5)})",
        status="running",
    )

    patched = generate_patch(
        source_code=state.get("patched_source") or state["source_code"],
        test_code=state["test_code"],
        error_log=state.get("error_log", ""),
        iteration=state["iteration"],
        source_file=source_file,
        language=language,
    )

    state["patched_source"] = patched
    state["patch_diff"] = unified_diff(
        state.get("original_source", ""),
        patched,
        path=source_file,
    )

    workspace = Path(state["workspace"])
    target = workspace / source_file
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(patched, encoding="utf-8")

    _emit(
        state,
        emit,
        "patch",
        message=f"Patch drafted for {source_file}",
        patched_source=patched,
        patch_diff=state["patch_diff"],
        original_source=state.get("original_source", ""),
    )
    return state


def run_sandbox_node(state: PatchState, emit: EmitFn | None = None) -> PatchState:
    state["active_node"] = "run_sandbox"
    runtime = state.get("runtime", "python")
    _emit(
        state,
        emit,
        "node",
        message=f"Spawning ephemeral {runtime} Docker sandbox (network disabled)",
    )

    def on_log(chunk: str) -> None:
        _emit(state, emit, "log", message=chunk)

    workspace = Path(state["workspace"])
    if runtime == "node":
        result = run_node_sandbox(
            workspace,
            state.get("test_command") or ["npm", "test"],
            image=os.getenv("DOCKER_NODE_IMAGE", "autopatch-node-sandbox:latest"),
            timeout_sec=int(os.getenv("SANDBOX_TIMEOUT_SEC", "120")),
            mem_limit=os.getenv("SANDBOX_MEM_LIMIT", "768m"),
            on_log=on_log,
        )
    else:
        result = run_pytest_sandbox(
            workspace,
            image=os.getenv("DOCKER_IMAGE", "autopatch-sandbox:latest"),
            timeout_sec=int(os.getenv("SANDBOX_TIMEOUT_SEC", "60")),
            mem_limit=os.getenv("SANDBOX_MEM_LIMIT", "256m"),
            on_log=on_log,
        )

    state["test_exit_code"] = result.exit_code
    state["error_log"] = result.stdout or result.stderr
    _emit(
        state,
        emit,
        "sandbox_result",
        message="Sandbox finished",
        exit_code=result.exit_code,
        duration_ms=result.duration_ms,
        error_log=state["error_log"],
    )
    return state


def evaluate_node(state: PatchState, emit: EmitFn | None = None) -> PatchState:
    state["active_node"] = "evaluate"
    exit_code = int(state.get("test_exit_code", 1))
    iteration = int(state.get("iteration", 0))
    max_iterations = int(state.get("max_iterations", 5))

    if exit_code == 0:
        state["status"] = "awaiting_approval"
        _emit(
            state,
            emit,
            "node",
            message="Tests passed — waiting for human approval",
            status="awaiting_approval",
        )
    elif iteration >= max_iterations:
        state["status"] = "failed"
        state["finished_at"] = time.time()
        _emit(
            state,
            emit,
            "failed",
            message=f"Gave up after {iteration} attempts",
            status="failed",
        )
    else:
        state["status"] = "running"
        _emit(
            state,
            emit,
            "node",
            message="Tests still red — feeding error back into the agent",
            status="running",
        )
    return state


def route_after_evaluate(state: PatchState) -> str:
    if state.get("status") == "awaiting_approval":
        return "await_approval"
    if state.get("status") == "failed":
        return "failed"
    return "generate_patch"


def await_approval_node(state: PatchState, emit: EmitFn | None = None) -> PatchState:
    state["active_node"] = "await_approval"
    state["status"] = "awaiting_approval"
    _emit(
        state,
        emit,
        "hitl",
        message="Human-in-the-loop gate — Approve to commit/PR, Reject to discard",
        status="awaiting_approval",
        patch_diff=state.get("patch_diff", ""),
        patched_source=state.get("patched_source", ""),
        original_source=state.get("original_source", ""),
    )
    return state


def commit_patch_node(state: PatchState, emit: EmitFn | None = None) -> PatchState:
    state["active_node"] = "commit_patch"
    decision = state.get("decision", "")
    if decision != "approve":
        state["status"] = "rejected"
        state["active_node"] = "rejected"
        state["finished_at"] = time.time()
        _emit(state, emit, "rejected", message="Patch rejected — nothing committed")
        return state

    workspace = Path(state["workspace"])
    source_file = state.get("source_file", "impl.py")
    fixture_id = state.get("fixture_id", "code")
    title = f"autopatch: fix {fixture_id} (iter {state.get('iteration', 0)})"
    sha = commit_patch(workspace, message=title, paths=[source_file])

    pr_url = None
    pr_note = ""
    try:
        pr_url = try_open_pull_request(
            workspace,
            run_id=state.get("run_id", "local"),
            fixture_id=fixture_id,
            title=title,
            body=(
                f"AutoPatch remediation for `{fixture_id}`.\n\n"
                f"Scoped file: `{source_file}`\n"
                f"Sandbox runtime: `{state.get('runtime', 'python')}`\n"
                f"Iterations: {state.get('iteration', 0)}\n\n"
                f"```diff\n{state.get('patch_diff', '')[:3500]}\n```\n"
            ),
            source_file=source_file,
        )
    except Exception as exc:
        pr_note = f" (PR skipped: {exc})"

    state["pr_url"] = pr_url or ""
    state["status"] = "committed"
    state["active_node"] = "committed"
    state["finished_at"] = time.time()

    if pr_url:
        msg = f"Committed {sha} and opened PR {pr_url}"
    else:
        msg = f"Committed locally as {sha}{pr_note}"

    _emit(
        state,
        emit,
        "committed",
        message=msg,
        commit_sha=sha,
        pr_url=pr_url or "",
    )
    return state


def failed_node(state: PatchState, emit: EmitFn | None = None) -> PatchState:
    state["active_node"] = "failed"
    state["status"] = "failed"
    state["finished_at"] = time.time()
    return state
