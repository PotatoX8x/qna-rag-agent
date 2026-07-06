from pydantic import BaseModel, Field


class HallucinationGrade(BaseModel):
    """Structured output for the hallucination check node."""

    grounded: bool = Field(
        description="True only if every substantive claim in the answer is supported by the context"
    )
