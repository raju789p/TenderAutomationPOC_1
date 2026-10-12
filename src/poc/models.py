"""Pydantic models for extracted document elements."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Span(BaseModel):
    """A text run with its source emphasis."""

    text: str
    bold: bool = False
    italic: bool = False


class Element(BaseModel):
    """Common identity and placement metadata for a source element."""

    model_config = ConfigDict(extra="forbid")

    id: str
    doc_id: str
    page: int = Field(ge=1)
    bbox: tuple[float, float, float, float]
    type: str
    role: Literal["cover", "toc", "body", "page_number"]
    disposition: Literal["placed", "regenerated", "unplaced", "pending"] = "pending"


class Heading(Element):
    type: Literal["heading"] = "heading"
    level: int = Field(ge=1)
    number: str | None = None
    title: str


class Paragraph(Element):
    type: Literal["paragraph"] = "paragraph"
    spans: list[Span]
    is_label: bool = False


class Bullet(Element):
    type: Literal["bullet"] = "bullet"
    spans: list[Span]
    level: int = Field(ge=0)


class Table(Element):
    type: Literal["table"] = "table"
    rows: list[list[str]]
    header_rows: int = Field(ge=0)
    n_rows: int = Field(ge=0)
    n_cols: int = Field(ge=0)


class ImageDescription(BaseModel):
    """Optional AI description metadata for a figure."""

    kind: Literal["photo", "diagram", "chart", "screenshot", "other"]
    caption: str
    transcribed_text: list[str]
    uncertain: bool
    provider: str
    model: str
    prompt_version: str

    @field_validator("caption")
    @classmethod
    def validate_one_sentence(cls, value: str) -> str:
        import re

        normalized = value.strip()
        if not normalized or "\n" in normalized or len(re.findall(r"[.!?](?:\s|$)", normalized)) > 1:
            raise ValueError("caption must be one non-empty sentence")
        return normalized


class HeadingClassification(BaseModel):
    """Canonical section type assigned to one heading."""

    canonical_type: Literal[
        "abstract", "scope", "introduction", "learning_objectives", "core_concept",
        "process_detail", "when_to_use", "best_practices", "advantages", "limitations",
    ]


class FigurePart(BaseModel):
    """One exact embedded image fragment belonging to a logical figure."""

    id: str
    page: int = Field(ge=1)
    xref: int
    image_path: str
    sha256: str
    bbox: tuple[float, float, float, float]
    width: int
    height: int
    mime: str
    colorspace: str
    mask_present: bool
    mask_xref: int | None = None
    mask_path: str | None = None
    mask_sha256: str | None = None
    mask_byte_size: int = 0
    byte_size: int


class Figure(Element):
    type: Literal["figure"] = "figure"
    image_path: str
    sha256: str
    width: int
    height: int
    mime: str
    origin: str
    parts: list[FigurePart] = Field(default_factory=list)
    ai: ImageDescription | None = None
    ai_status: Literal["pending", "complete", "failed"] = "pending"
    ai_error: str | None = None


class PageNumber(Element):
    type: Literal["page_number"] = "page_number"
    role: Literal["page_number"] = "page_number"
    value: str


DocumentElement = Annotated[
    Heading | Paragraph | Bullet | Table | Figure | PageNumber,
    Field(discriminator="type"),
]


class Document(BaseModel):
    """Document inventory and extracted elements."""

    doc_id: str
    source_file: str
    source_sha256: str
    page_count: int = Field(ge=0)
    elements: list[DocumentElement]
    cover_lines: list[str]
