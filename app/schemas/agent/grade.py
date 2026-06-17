from pydantic import BaseModel


class DocumentGrade(BaseModel):
    """Structured output for the document grading node."""

    relevant_indices: list[int]
    needs_web_search: bool
