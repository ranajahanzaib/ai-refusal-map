"""Validated API payloads."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Outcome = Literal[
    "full_compliance",
    "partial_compliance",
    "full_refusal",
    "clarification",
    "conditional_assistance",
    "non_answer",
    "indeterminate",
]


class AnnotationInput(BaseModel):
    pair_id: str = Field(min_length=1, max_length=200)
    annotator_id: str = Field(min_length=1, max_length=100)
    outcome: Outcome
    stated_reasons: list[str] = Field(default_factory=list, max_length=10)
    alternative_types: list[str] = Field(default_factory=list, max_length=10)
    justification: str | None = Field(default=None, max_length=40)
    comment: str | None = Field(default=None, max_length=4000)


class Annotation(AnnotationInput):
    annotation_id: str
    created_at: datetime
    revision: int
