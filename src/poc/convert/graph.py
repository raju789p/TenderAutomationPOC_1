"""LangGraph plan → validate → bounded repair → deterministic fallback flow."""

from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, StateGraph
from pydantic import ValidationError

from poc.convert.assemble import fallback_section, validate_chunk_plan
from poc.convert.plan_schema import Plan, PlanSection
from poc.convert.planner import element_preview, planner_runnable
from poc.llm.service import InvalidProviderOutput


class ChunkState(TypedDict, total=False):
    chunk: dict[str, Any]
    outline: list[dict[str, Any]]
    instructions: str
    runnable: Any
    classification_config: dict[str, Any]
    target_config: dict[str, Any]
    attempts: int
    validation_errors: str
    plan: Plan
    section: PlanSection
    fallback_used: bool
    fallback_reason: str | None


def build_chunk_graph(model: Any):
    """Compile the chunk graph. At most two repair calls follow the first attempt."""
    def plan_node(state: ChunkState) -> dict[str, Any]:
        chunk = state["chunk"]
        previews = [element_preview(e) for e in chunk["elements"]]
        outline = state.get("outline", [])
        runnable = state.get("runnable") or planner_runnable(model, state["instructions"])
        try:
            result = runnable.invoke({
                "outline": outline,
                "chunk_json": previews,
                "validation_errors": state.get("validation_errors", "none"),
            })
        except (InvalidProviderOutput, ValidationError, ValueError) as error:
            return {
                "plan": None,
                "attempts": state.get("attempts", 0) + 1,
                "validation_errors": f"Structured Plan validation failed: {type(error).__name__}: {error}",
            }
        return {"plan": result, "attempts": state.get("attempts", 0) + 1}

    def validate_node(state: ChunkState) -> dict[str, Any]:
        if state.get("plan") is None:
            return {"section": None, "validation_errors": state.get("validation_errors", "Plan validation failed")}
        try:
            section = validate_chunk_plan(state["plan"], state["chunk"])
            return {"section": section, "validation_errors": ""}
        except ValueError as error:
            return {"validation_errors": str(error)}

    def route_after_validation(state: ChunkState) -> str:
        if state.get("section") is not None:
            return "done"
        if state.get("attempts", 0) <= 2:
            return "retry"
        return "fallback"

    def fallback_node(state: ChunkState) -> dict[str, Any]:
        reason = state.get("validation_errors", "plan validation failed")
        section = fallback_section(state["chunk"], state["classification_config"], state["target_config"])
        return {"section": section, "fallback_used": True, "fallback_reason": reason}

    graph = StateGraph(ChunkState)
    graph.add_node("plan", plan_node)
    graph.add_node("validate", validate_node)
    graph.add_node("fallback", fallback_node)
    graph.set_entry_point("plan")
    graph.add_edge("plan", "validate")
    graph.add_conditional_edges("validate", route_after_validation, {"done": END, "retry": "plan", "fallback": "fallback"})
    graph.add_edge("fallback", END)
    return graph.compile()


def plan_chunk(model: Any, state: ChunkState) -> ChunkState:
    """Run one chunk through graph validation and return its counters and disposition."""
    return build_chunk_graph(model).invoke(state)
