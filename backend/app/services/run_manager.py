"""In-memory run store + background LangGraph execution for the demo."""

from __future__ import annotations

import asyncio
import os
import tempfile
import time
import traceback
import uuid
from pathlib import Path
from typing import Any

from langgraph.errors import GraphInterrupt
from langgraph.types import Command

from app.graph.workflow import build_graph
from app.services.fixtures import get_spec, load_fixture


class RunManager:
    def __init__(self) -> None:
        self._runs: dict[str, dict[str, Any]] = {}
        self._queues: dict[str, list[asyncio.Queue]] = {}
        self._lock = asyncio.Lock()

    def list_runs(self) -> list[dict[str, Any]]:
        return [self._public(run) for run in self._runs.values()]

    def get(self, run_id: str) -> dict[str, Any] | None:
        run = self._runs.get(run_id)
        return self._public(run) if run else None

    async def subscribe(self, run_id: str) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        async with self._lock:
            self._queues.setdefault(run_id, []).append(queue)
            run = self._runs.get(run_id)
            if run:
                for event in run.get("events", []):
                    await queue.put(event)
        return queue

    async def unsubscribe(self, run_id: str, queue: asyncio.Queue) -> None:
        async with self._lock:
            listeners = self._queues.get(run_id, [])
            if queue in listeners:
                listeners.remove(queue)

    async def _broadcast(self, run_id: str, event: dict[str, Any]) -> None:
        run = self._runs.get(run_id)
        if run is not None:
            run.setdefault("events", []).append(event)
            for key in (
                "status",
                "active_node",
                "iteration",
                "patch_diff",
                "patched_source",
                "original_source",
                "error_log",
                "test_exit_code",
                "message",
                "pr_url",
                "runtime",
                "source_file",
            ):
                if key in event:
                    run[key] = event[key]
            if "exit_code" in event:
                run["test_exit_code"] = event["exit_code"]
            if event.get("type") in {"committed", "rejected", "failed"}:
                run["status"] = event["type"] if event["type"] != "committed" else "committed"
                if event["type"] == "committed":
                    run["commit_sha"] = event.get("commit_sha")
                    if event.get("pr_url"):
                        run["pr_url"] = event["pr_url"]
                run["finished_at"] = event.get("ts", time.time())

        for queue in list(self._queues.get(run_id, [])):
            await queue.put(event)

    def _public(self, run: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": run["id"],
            "fixture_id": run.get("fixture_id"),
            "status": run.get("status", "queued"),
            "active_node": run.get("active_node", "idle"),
            "iteration": run.get("iteration", 0),
            "max_iterations": run.get("max_iterations", 5),
            "patch_diff": run.get("patch_diff", ""),
            "original_source": run.get("original_source", ""),
            "patched_source": run.get("patched_source", ""),
            "error_log": run.get("error_log", ""),
            "test_exit_code": run.get("test_exit_code"),
            "commit_sha": run.get("commit_sha"),
            "pr_url": run.get("pr_url"),
            "runtime": run.get("runtime"),
            "source_file": run.get("source_file"),
            "started_at": run.get("started_at"),
            "finished_at": run.get("finished_at"),
            "workspace": run.get("workspace"),
            "ci_repo": run.get("ci_repo"),
            "ci_branch": run.get("ci_branch"),
            "ci_commit": run.get("ci_commit"),
        }

    async def start_fixture_run(
        self,
        fixture_id: str,
        max_iterations: int | None = None,
        *,
        seed_error_log: str = "",
        ci_repo: str = "",
        ci_branch: str = "",
        ci_commit: str = "",
    ) -> dict[str, Any]:
        source, tests, _ = load_fixture(fixture_id)
        spec = get_spec(fixture_id)
        return await self.start_run(
            fixture_id=fixture_id,
            source_code=source,
            test_code=tests,
            max_iterations=max_iterations,
            runtime=spec.runtime,
            source_file=spec.source_file,
            seed_error_log=seed_error_log,
            ci_repo=ci_repo,
            ci_branch=ci_branch,
            ci_commit=ci_commit,
        )

    def _assert_docker(self) -> None:
        try:
            import docker

            docker.from_env().ping()
        except Exception as exc:
            raise RuntimeError(
                "Docker is not reachable. Start Docker Desktop, then retry."
            ) from exc

    async def start_run(
        self,
        *,
        fixture_id: str,
        source_code: str,
        test_code: str,
        max_iterations: int | None = None,
        runtime: str = "python",
        source_file: str = "impl.py",
        seed_error_log: str = "",
        ci_repo: str = "",
        ci_branch: str = "",
        ci_commit: str = "",
    ) -> dict[str, Any]:
        self._assert_docker()
        if not os.getenv("GEMINI_API_KEY"):
            raise RuntimeError(
                "GEMINI_API_KEY is empty — add it to backend/.env (free from Google AI Studio)."
            )

        run_id = uuid.uuid4().hex[:10]
        workspace = Path(tempfile.mkdtemp(prefix=f"autopatch-{run_id}-"))
        max_iter = max_iterations or int(os.getenv("MAX_ITERATIONS", "5"))

        run = {
            "id": run_id,
            "fixture_id": fixture_id,
            "status": "queued",
            "active_node": "idle",
            "iteration": 0,
            "max_iterations": max_iter,
            "workspace": str(workspace),
            "original_source": source_code,
            "patched_source": source_code,
            "runtime": runtime,
            "source_file": source_file,
            "events": [],
            "started_at": time.time(),
            "thread_id": run_id,
            "ci_repo": ci_repo,
            "ci_branch": ci_branch,
            "ci_commit": ci_commit,
        }
        self._runs[run_id] = run

        if ci_repo:
            os.environ.setdefault("GITHUB_REPOSITORY", ci_repo)

        initial: dict[str, Any] = {
            "run_id": run_id,
            "fixture_id": fixture_id,
            "workspace": str(workspace),
            "source_code": source_code,
            "test_code": test_code,
            "original_source": source_code,
            "patched_source": source_code,
            "error_log": seed_error_log,
            "seed_error_log": seed_error_log,
            "patch_diff": "",
            "iteration": 0,
            "max_iterations": max_iter,
            "test_exit_code": 1,
            "status": "queued",
            "active_node": "idle",
            "events": [],
            "decision": "",
            "runtime": runtime,
            "source_file": source_file,
            "ci_repo": ci_repo,
            "ci_branch": ci_branch,
            "ci_commit": ci_commit,
            "pr_url": "",
        }

        asyncio.create_task(self._execute(run_id, initial))
        return self._public(run)

    async def _execute(self, run_id: str, initial: dict[str, Any]) -> None:
        loop = asyncio.get_running_loop()

        def emit(event: dict[str, Any]) -> None:
            asyncio.run_coroutine_threadsafe(self._broadcast(run_id, event), loop)

        graph = build_graph(emit)
        config = {"configurable": {"thread_id": run_id}, "recursion_limit": 40}

        try:
            await self._broadcast(
                run_id,
                {
                    "type": "status",
                    "run_id": run_id,
                    "ts": time.time(),
                    "status": "running",
                    "active_node": "ingest",
                    "message": "Run started",
                },
            )
            try:
                await asyncio.to_thread(graph.invoke, initial, config)
            except GraphInterrupt:
                pass

            snap = graph.get_state(config)
            run = self._runs[run_id]
            if snap and snap.next:
                run["status"] = "awaiting_approval"
                run["active_node"] = "await_approval"
                run["graph"] = graph
                run["config"] = config
                values = snap.values or {}
                for key in (
                    "patch_diff",
                    "patched_source",
                    "original_source",
                    "iteration",
                    "runtime",
                    "source_file",
                ):
                    if values.get(key) is not None:
                        run[key] = values[key]
            else:
                if run.get("status") not in {
                    "committed",
                    "rejected",
                    "failed",
                    "awaiting_approval",
                }:
                    values = snap.values if snap else {}
                    run["status"] = values.get("status", "failed")
                    run["active_node"] = values.get("active_node", "failed")
                    run["finished_at"] = time.time()
        except Exception as exc:
            tb = traceback.format_exc()
            await self._broadcast(
                run_id,
                {
                    "type": "error",
                    "run_id": run_id,
                    "ts": time.time(),
                    "status": "failed",
                    "active_node": "failed",
                    "message": str(exc),
                    "error_log": tb,
                },
            )
            self._runs[run_id]["status"] = "failed"
            self._runs[run_id]["finished_at"] = time.time()

    async def decide(self, run_id: str, decision: str) -> dict[str, Any]:
        run = self._runs.get(run_id)
        if not run:
            raise KeyError(run_id)
        if run.get("status") != "awaiting_approval":
            raise RuntimeError(f"Run is not awaiting approval (status={run.get('status')})")

        graph = run.get("graph")
        config = run.get("config")
        if graph is None or config is None:
            raise RuntimeError("Graph checkpoint missing — cannot resume")

        await self._broadcast(
            run_id,
            {
                "type": "status",
                "run_id": run_id,
                "ts": time.time(),
                "message": f"Human decided: {decision}",
                "status": "running",
                "active_node": "commit_patch",
            },
        )

        def resume() -> None:
            graph.invoke(Command(resume={"decision": decision}), config)

        await asyncio.to_thread(resume)
        snap = graph.get_state(config)
        values = snap.values if snap else {}
        run["status"] = values.get("status", decision)
        run["active_node"] = values.get("active_node", decision)
        run["finished_at"] = time.time()
        run["decision"] = decision
        if values.get("pr_url"):
            run["pr_url"] = values["pr_url"]
        if values.get("commit_sha") or run.get("commit_sha"):
            pass
        return self._public(run)


manager = RunManager()
