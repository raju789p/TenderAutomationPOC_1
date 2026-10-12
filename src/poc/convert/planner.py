"""LangChain prompt and provider adapter for source-id-only placement plans."""

from __future__ import annotations

import json
import ast
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda

from poc.convert.plan_schema import Plan


PROMPT_VERSION = "c1-plan-v1"
_PROMPT = """Assign each source id to one target section. Return JSON only.
Allowed target_section: A_overview, B_core_concept, C_process_detail, D_fit_check,
E_strengths_risks, F_learning_checklist, unclassified.
Allowed block_type: heading, paragraph, bullet, table, image.
Do not create, edit, merge, drop, or reorder source content. Keep source ids and types exact.
Outline: {outline}
Validation feedback: {validation_errors}
Current source chunk (JSON): {chunk_json}
"""


def make_prompt(instructions: str) -> ChatPromptTemplate:
    """Create the pinned C1 LangChain prompt template."""
    return ChatPromptTemplate.from_messages([
        ("system", f"Prompt version {PROMPT_VERSION}. Placement decisions only.\n\n{instructions}"),
        ("human", _PROMPT),
    ])


class ProviderPlanAdapter:
    """Expose the existing validated provider service as a LangChain structured model."""

    def __init__(self, service: Any, call_log: Path, ids: list[str]):
        self.service = service
        self.call_log = call_log
        self.ids = ids

    def with_structured_output(self, schema: type[Plan]) -> RunnableLambda:
        """Return a LangChain runnable validating and caching the structured response."""
        def invoke(prompt_value: Any) -> Plan:
            prompt_text = prompt_value.to_string()
            before_calls = self.service.stats.provider_calls
            before_retries = self.service.stats.retries
            try:
                result, cached = self.service.generate_validated(prompt_text, schema)
            except Exception as error:
                entry = {
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "prompt_version": PROMPT_VERSION,
                    "ids_sent": self.ids,
                    "token_usage": None,
                    "result": "FAILED",
                    "error_type": type(error).__name__,
                    "error": str(error)[:2000] if type(error).__name__ == "ProviderError" else type(error).__name__,
                    "cache_hit": False,
                    "provider_calls": self.service.stats.provider_calls - before_calls,
                    "retries": self.service.stats.retries - before_retries,
                }
                self._append_log(entry)
                raise
            call_count = self.service.stats.provider_calls - before_calls
            entry = {
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "prompt_version": PROMPT_VERSION,
                "ids_sent": self.ids,
                "token_usage": None,
                "result": result.model_dump(mode="json"),
                "cache_hit": cached,
                "provider_calls": call_count,
                "retries": self.service.stats.retries - before_retries,
            }
            self._append_log(entry)
            return result

        return RunnableLambda(invoke)

    def _append_log(self, entry: dict[str, Any]) -> None:
        """Append a sanitized, credential-free structured call record."""
        self.call_log.parent.mkdir(parents=True, exist_ok=True)
        entries = json.loads(self.call_log.read_text(encoding="utf-8")) if self.call_log.exists() else []
        entries.append(entry)
        self.call_log.write_text(json.dumps(entries, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def planner_runnable(model: Any, instructions: str) -> Any:
    """Build the prompt → model structured output runnable used by the graph."""
    return make_prompt(instructions) | model.with_structured_output(Plan)


def compact_planner_instructions(target_config: dict[str, Any]) -> str:
    """Build concise, configuration-derived target descriptions for the planner."""
    descriptions = {
        "abstract": "purpose and summary", "scope": "boundaries and applicability",
        "introduction": "context and background", "learning_objectives": "learner outcomes",
        "core_concept": "principles and terminology", "process_detail": "steps and workflow",
        "when_to_use": "fit and selection criteria", "best_practices": "recommended practice",
        "advantages": "strengths", "limitations": "risks and constraints",
    }
    lines = ["Place every element exactly once; preserve hierarchy and order. Do not rewrite content."]
    for section in target_config.get("sections", []):
        accepted = ", ".join(
            f"{canonical} ({descriptions.get(canonical, canonical)})"
            for canonical in section.get("accepts", [])
        )
        lines.append(f"{section['id']}: {accepted}.")
    lines.extend([
        "Keep tables and images as their own block types. Use unclassified if uncertain.",
        "Include page-number and contents elements once; renderer regenerates their display.",
    ])
    return "\n".join(lines)


class MockPlanProvider:
    """Offline deterministic provider that places every chunk in unclassified."""

    name = "mock"
    model = "mock-plan-v1"

    def model_for(self, image: bool = False) -> str:
        """Return the stable offline model label."""
        return self.model

    def generate_json(self, prompt: str, schema: type[Plan], image: bytes | None = None, mime: str | None = None) -> dict[str, Any]:
        """Return a structurally complete plan derived only from prompt ids and types."""
        marker = "Current source chunk (JSON): "
        elements = ast.literal_eval(prompt.rsplit(marker, 1)[1].strip())
        heading_id = next((item["id"] for item in elements if item.get("type") == "heading" and item.get("level") == 1), None)
        block_map = {"image": "image", "page_number": "paragraph"}
        return {
            "sections": [{
                "target_section": "unclassified",
                "source_heading_id": heading_id,
                "blocks": [{"source_id": item["id"], "block_type": block_map.get(item["type"], item["type"])} for item in elements],
            }]
        }


def element_preview(element: dict[str, Any], preview_chars: int = 160) -> dict[str, Any]:
    """Reduce an IR element to the permitted, path-free prompt fields."""
    kind = element.get("type")
    item: dict[str, Any] = {
        "id": element["id"],
        "type": {"figure": "image"}.get(kind, kind),
        "page": element.get("page", 0),
    }
    if kind == "heading":
        item.update(level=element.get("level"), number=element.get("number"), text=element.get("title", "")[:preview_chars])
    elif kind in {"paragraph", "bullet"}:
        item["text"] = "".join(span.get("text", "") for span in element.get("spans", []))[:preview_chars]
    elif kind == "table":
        rows = element.get("rows", [])
        item["table_preview"] = {
            "shape": [element.get("n_rows", len(rows)), element.get("n_cols", max((len(row) for row in rows), default=0))],
            "header_row": [str(cell)[:80] for cell in rows[0]] if rows else [],
        }
    elif kind == "figure":
        ai = element.get("ai") or {}
        item["image"] = {"id": element["id"], "caption": ai.get("caption", "")}
    elif kind == "page_number":
        item["text"] = element.get("value", "")
    return item
