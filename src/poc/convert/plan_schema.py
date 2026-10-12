"""Strict schema for element-id-only conversion plans."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


TargetSection = Literal[
    "A_overview", "B_core_concept", "C_process_detail", "D_fit_check",
    "E_strengths_risks", "F_learning_checklist", "unclassified",
]
BlockType = Literal["heading", "paragraph", "bullet", "table", "image"]


def gemini_plan_schema() -> dict[str, object]:
    """Return the flat Gemini response schema; strict value checks remain local."""
    return {
        "type": "OBJECT",
        "properties": {
            "sections": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "target_section": {"type": "STRING"},
                        "source_heading_id": {"type": "STRING", "nullable": True},
                        "blocks": {
                            "type": "ARRAY",
                            "items": {
                                "type": "OBJECT",
                                "properties": {
                                    "source_id": {"type": "STRING"},
                                    "block_type": {"type": "STRING"},
                                },
                                "required": ["source_id", "block_type"],
                            },
                        },
                    },
                    "required": ["target_section", "source_heading_id", "blocks"],
                },
            },
        },
        "required": ["sections"],
    }


class PlanBlock(BaseModel):
    """A reference to one source IR element, without replacement content."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    source_id: str = Field(min_length=1)
    block_type: BlockType


class PlanSection(BaseModel):
    """One top-level source section's target and ordered element references."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    target_section: TargetSection
    source_heading_id: str | None
    blocks: list[PlanBlock]


class Plan(BaseModel):
    """A complete id-only placement plan for one chunk or document."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    sections: list[PlanSection]

    @staticmethod
    def gemini_response_schema() -> dict[str, object]:
        """Return the simplified provider schema; Plan remains strict locally."""
        return gemini_plan_schema()
