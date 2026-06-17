from pydantic import BaseModel


class GenerateOutput(BaseModel):
    """Structured output for the generation node."""

    answer: str
    cited_indices: list[int]
