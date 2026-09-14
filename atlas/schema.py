from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator


class Edge(BaseModel):
    source: str
    relation: str
    target: str
    evidence: str = Field(min_length=1)


class Document(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(pattern=r"^[A-Za-z0-9_.-]{1,120}$")
    title: str = Field(min_length=1, max_length=300)
    text: str = Field(min_length=1, max_length=200_000)
    project: str = "public"
    kind: str = "reference"
    source: str
    synthetic: bool = False
    current: bool = True
    date: str = "2026-01-01"
    edges: list[Edge] = Field(default_factory=list, max_length=100)
    channel: Literal["documents", "email", "slack", "teams"] = "documents"
    thread_id: str | None = Field(default=None, max_length=200)
    author: str | None = Field(default=None, max_length=200)
    decision_status: Literal["unspecified", "proposed", "approved", "recorded", "disputed"] = "unspecified"

    @field_validator("text")
    @classmethod
    def nonblank_text(cls,value):
        if not value.strip():
            raise ValueError("Document text cannot be blank")
        return value

    @field_validator("source")
    @classmethod
    def safe_source(cls, value):
        if not value.startswith(("https://", "synthetic:", "upload:")):
            raise ValueError("Source must use https:, synthetic: or upload:")
        return value


class Chunk(BaseModel):
    id: str
    doc_id: str
    text: str
    start: int
    end: int


class Question(BaseModel):
    id: str
    query: str
    relevant: list[str]
    answer_terms: list[str] = Field(default_factory=list)
    category: str
    split: str
    projects: list[str] = Field(default_factory=list)


class QueryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=3, max_length=1000)
    k: int = Field(default=5, ge=1, le=10)
    mode: Literal["auto", "vector", "hybrid", "graph", "investigate"] = "auto"
    generation: Literal["evidence", "local"] = "evidence"
    project: str | None = None
    sources: list[Literal["documents", "email", "slack", "teams"]] = Field(default_factory=lambda: ["documents"], min_length=1, max_length=4)
