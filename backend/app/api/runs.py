"""HTTP surface for starting runs, streaming events, CI hooks, and HITL decisions."""

from __future__ import annotations

import asyncio
import json
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from app.services.fixtures import list_fixtures
from app.services.run_manager import manager

router = APIRouter()


class StartRunBody(BaseModel):
    fixture_id: str = Field(..., examples=["nextjs_pricing", "off_by_one"])
    max_iterations: int | None = Field(default=None, ge=1, le=10)


class DecisionBody(BaseModel):
    decision: Literal["approve", "reject"]


class CiFailureBody(BaseModel):
    """Payload shape a GitHub Action (or any CI) can POST when tests go red."""

    fixture_id: str = Field(
        default="nextjs_pricing",
        description="Which scoped sample/project AutoPatch should remediate",
    )
    error_log: str = Field(..., min_length=1, description="Failing job log / jest output")
    repo: str | None = Field(default=None, examples=["acme/storefront"])
    branch: str | None = Field(default=None, examples=["main"])
    commit_sha: str | None = None
    max_iterations: int | None = Field(default=None, ge=1, le=10)


@router.get("/fixtures")
def get_fixtures() -> list[dict[str, str]]:
    return list_fixtures()


@router.get("/runs")
def get_runs() -> list[dict[str, Any]]:
    return manager.list_runs()


@router.post("/runs")
async def start_run(body: StartRunBody) -> dict[str, Any]:
    try:
        return await manager.start_fixture_run(body.fixture_id, body.max_iterations)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/ci/failures")
async def ci_failure(body: CiFailureBody) -> dict[str, Any]:
    """CI entrypoint — same remediation brain, kicked by a failing pipeline."""
    try:
        run = await manager.start_fixture_run(
            body.fixture_id,
            body.max_iterations,
            seed_error_log=body.error_log,
            ci_repo=body.repo or "",
            ci_branch=body.branch or "",
            ci_commit=body.commit_sha or "",
        )
        return {
            "ok": True,
            "run": run,
            "dashboard_hint": f"Open the UI and watch run {run['id']} — approve to commit/PR",
        }
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/runs/{run_id}")
def get_run(run_id: str) -> dict[str, Any]:
    run = manager.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.get("/runs/{run_id}/events")
async def stream_events(run_id: str) -> EventSourceResponse:
    if not manager.get(run_id):
        raise HTTPException(status_code=404, detail="Run not found")

    queue = await manager.subscribe(run_id)

    async def gen():
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield {
                        "event": event.get("type", "message"),
                        "data": json.dumps(event),
                    }
                    if event.get("type") in {"committed", "rejected", "failed", "error"}:
                        await asyncio.sleep(0.05)
                        break
                except asyncio.TimeoutError:
                    yield {"event": "ping", "data": "{}"}
        finally:
            await manager.unsubscribe(run_id, queue)

    return EventSourceResponse(gen())


@router.post("/runs/{run_id}/decision")
async def decide(run_id: str, body: DecisionBody) -> dict[str, Any]:
    try:
        return await manager.decide(run_id, body.decision)
    except KeyError:
        raise HTTPException(status_code=404, detail="Run not found") from None
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
