from abc import ABC, abstractmethod

from pydantic import BaseModel


class BaseLLMClient(ABC):
    """Provider-agnostic chat interface the rest of the app depends on."""

    @abstractmethod
    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.4,
        max_tokens: int | None = None,
    ) -> str:
        """Return a plain-text completion."""

    @abstractmethod
    async def complete_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: type[BaseModel],
        messages: list[dict] | None = None,
    ) -> BaseModel:
        """Return a validated ``schema`` instance via the model's structured output."""

    @abstractmethod
    async def stream(
        self,
        system_prompt: str,
        user_prompt: str,
        messages: list[dict] | None = None,
    ):
        """Yield response text deltas."""
