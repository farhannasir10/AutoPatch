"""Cyclic LangGraph workflow: patch → sandbox → evaluate → (retry | HITL)."""

from __future__ import annotations

from typing import Any, Callable

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.types import interrupt

from app.graph.nodes import (
    await_approval_node,
    commit_patch_node,
    evaluate_node,
    failed_node,
    generate_patch_node,
    ingest_node,
    route_after_evaluate,
    run_sandbox_node,
)
from app.graph.state import PatchState

EmitFn = Callable[[dict[str, Any]], None]


def build_graph(emit: EmitFn | None = None):
    """Bind an emit callback into each node without baking UI into the graph defs."""

    def ingest(state: PatchState) -> PatchState:
        return ingest_node(state, emit)

    def patch(state: PatchState) -> PatchState:
        return generate_patch_node(state, emit)

    def sandbox(state: PatchState) -> PatchState:
        return run_sandbox_node(state, emit)

    def evaluate(state: PatchState) -> PatchState:
        return evaluate_node(state, emit)

    def await_approval(state: PatchState) -> PatchState:
        # pause the graph here — resume with {"decision": "approve"|"reject"}
        await_approval_node(state, emit)
        decision = interrupt({"kind": "hitl", "run_id": state.get("run_id")})
        if isinstance(decision, dict):
            state["decision"] = decision.get("decision", "reject")
        else:
            state["decision"] = str(decision)
        return state

    def commit(state: PatchState) -> PatchState:
        return commit_patch_node(state, emit)

    def failed(state: PatchState) -> PatchState:
        return failed_node(state, emit)

    graph = StateGraph(PatchState)
    graph.add_node("ingest", ingest)
    graph.add_node("generate_patch", patch)
    graph.add_node("run_sandbox", sandbox)
    graph.add_node("evaluate", evaluate)
    graph.add_node("await_approval", await_approval)
    graph.add_node("commit_patch", commit)
    graph.add_node("failed", failed)

    graph.set_entry_point("ingest")
    # first pass: run tests before asking the model, so we have a real traceback
    graph.add_edge("ingest", "run_sandbox")
    graph.add_edge("run_sandbox", "evaluate")
    graph.add_conditional_edges(
        "evaluate",
        route_after_evaluate,
        {
            "generate_patch": "generate_patch",
            "await_approval": "await_approval",
            "failed": "failed",
        },
    )
    graph.add_edge("generate_patch", "run_sandbox")
    graph.add_edge("await_approval", "commit_patch")
    graph.add_edge("commit_patch", END)
    graph.add_edge("failed", END)

    memory = MemorySaver()
    return graph.compile(checkpointer=memory)
