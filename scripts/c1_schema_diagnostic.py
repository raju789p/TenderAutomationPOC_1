"""Write an offline diagnostic of the current C1 planner schema and prompt size."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from poc.convert.assemble import chunk_elements
from poc.convert.plan_schema import Plan
from poc.convert.planner import compact_planner_instructions, element_preview, make_prompt


ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN = {
    "$defs", "$ref", "anyOf", "oneOf", "enum", "additionalProperties",
    "default", "title",
}


def find_keywords(value: Any, path: str = "$") -> list[str]:
    """Return JSON paths where provider-incompatible schema keywords occur."""
    found: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key in FORBIDDEN:
                found.append(f"{path}/{key}")
            found.extend(find_keywords(item, f"{path}/{key}"))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found.extend(find_keywords(item, f"{path}/{index}"))
    return found


def main() -> None:
    """Write schema and prompt-size evidence without loading runtime settings."""
    payload = json.loads((ROOT / "data/work/waterfall/elements.json").read_text(encoding="utf-8"))
    chunks = chunk_elements(payload["elements"])
    chunk = chunks[0]
    import yaml

    target_config = yaml.safe_load((ROOT / "config/target_format.yaml").read_text(encoding="utf-8"))
    prompt = make_prompt(compact_planner_instructions(target_config)).format_prompt(
        outline=[
            {"id": item["id"], "title": item.get("title", "")[:100], "level": item.get("level", 1)}
            for item in payload["elements"] if item.get("type") == "heading" and int(item.get("level", 1)) == 1
        ],
        chunk_json=[element_preview(item) for item in chunk["elements"]],
        validation_errors="none",
    ).to_string()
    schema = Plan.model_json_schema()
    result = {
        "schema_sent_before_fix": json.loads((ROOT / "docs/c1_gemini_schema_diagnostic.json").read_text(encoding="utf-8"))["schema_sent_before_fix"],
        "prompt_size_before_fix": json.loads((ROOT / "docs/c1_gemini_schema_diagnostic.json").read_text(encoding="utf-8"))["prompt_size_before_fix"],
        "schema_sent_after_fix": Plan.gemini_response_schema(),
        "prompt_size_after_fix": {
            "characters": len(prompt),
            "approx_tokens_chars_div_4": (len(prompt) + 3) // 4,
            "estimate_method": "characters divided by four; rough estimate",
        },
        "unsupported_schema_keywords_found_before_fix": json.loads((ROOT / "docs/c1_gemini_schema_diagnostic.json").read_text(encoding="utf-8"))["unsupported_schema_keywords_found_before_fix"],
        "unsupported_schema_keywords_found_after_fix": sorted(find_keywords(Plan.gemini_response_schema())),
        "one_chunk_heading_id": chunk["source_heading_id"],
        "chunk_element_count": len(chunk["elements"]),
    }
    (ROOT / "docs/c1_gemini_schema_diagnostic.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
