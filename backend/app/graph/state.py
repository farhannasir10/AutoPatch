"""Shared state that walks the remediation cycle."""

from __future__ import annotations

from typing import Any, Literal, TypedDict


NodeName = Literal[
    "idle",
    "ingest",
    "generate_patch",
    "run_sandbox",
    "evaluate",
    "await_approval",
    "commit_patch",
    "failed",
    "rejected",
    "committed",
]


class PatchState(TypedDict, total=False):
    run_id: str
    fixture_id: str
    workspace: str
    source_code: str
    test_code: str
    original_source: str
    error_log: str
    patched_source: str
    patch_diff: str
    iteration: int
    max_iterations: int
    test_exit_code: int
    status: str
    active_node: NodeName
    events: list[dict[str, Any]]
    started_at: float
    finished_at: float
    decision: str  # approve | reject | ""
    # multi-runtime / CI fields
    runtime: str
    language: str
    source_file: str
    test_file: str
    test_command: list[str]
    pr_url: str
    ci_repo: str
    ci_branch: str
    ci_commit: str
    seed_error_log: str
