from pydantic import BaseModel


class HallucinationGrade(BaseModel):
    """Structured output for the hallucination check node."""

    grounded: bool
