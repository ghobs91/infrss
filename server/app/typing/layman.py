"""Schemas for layman summaries of primary-source documents."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LaymanSummaryUpsert(BaseModel):
    """A structured plain-language summary supplied by a client (WebLLM/Ollama) or the server."""

    # ``model_identifier`` intentionally mirrors the spec's modelIdentifier; opt out of Pydantic's
    # protected ``model_`` namespace so the field name is allowed.
    model_config = ConfigDict(protected_namespaces=())

    headline: str = Field(..., description="One sentence on the principal event or action")
    what_happened: list[str] = Field(default_factory=list, description="Fact-based bullet points")
    key_impact: str = Field(..., description="Practical real-world impact or requirement")
    model_identifier: str = Field(..., description="Model that produced the summary")


class LaymanSummaryRead(LaymanSummaryUpsert):
    """Stored layman summary as returned to clients."""

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    generated_at: datetime
