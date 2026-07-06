from pydantic import BaseModel, Field


class DocumentGrade(BaseModel):
    """Structured output for the document grading node."""

    relevant_indices: list[int] = Field(
        description="0-based indices of retrieved documents that are relevant to the query"
    )
    needs_web_search: bool = Field(
        description="True when fewer than 2 documents are relevant or the context is insufficient"
    )
