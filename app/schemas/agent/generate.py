from pydantic import BaseModel, Field


class GenerateOutput(BaseModel):
    """Structured output for the generation node."""

    answer: str = Field(description="Answer grounded solely in the provided context documents")
    cited_indices: list[int] = Field(
        description="0-based indices of context documents actually used to produce the answer"
    )
