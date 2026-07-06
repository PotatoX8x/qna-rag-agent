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
        fast: bool = False,
    ) -> str:
        """Return a plain-text completion.

        Parameters
        ----------
        system_prompt : str
            Instruction context prepended to every conversation.
        user_prompt : str
            The user's message for this turn.
        temperature : float, optional
            Sampling temperature. Default is 0.4.
        max_tokens : int or None, optional
            Hard cap on output tokens. ``None`` uses the model default.
        fast : bool, optional
            Use the lighter/cheaper model instead of the main analysis model.

        Returns
        -------
        str
            Full response text.
        """

    @abstractmethod
    async def complete_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: type[BaseModel],
        messages: list[dict] | None = None,
    ) -> BaseModel:
        """Return a validated Pydantic model via the provider's structured-output mode.

        Parameters
        ----------
        system_prompt : str
            Instruction context.
        user_prompt : str
            The user's message for this turn.
        schema : type[BaseModel]
            Pydantic model class the response must conform to.
        messages : list[dict] or None, optional
            Prior conversation turns as ``[{"role": ..., "content": ...}]``.

        Returns
        -------
        BaseModel
            Parsed and validated instance of ``schema``.
        """

    @abstractmethod
    async def stream(
        self,
        system_prompt: str,
        user_prompt: str,
        messages: list[dict] | None = None,
    ):
        """Yield response text deltas as they arrive from the model.

        Parameters
        ----------
        system_prompt : str
            Instruction context.
        user_prompt : str
            The user's message for this turn.
        messages : list[dict] or None, optional
            Prior conversation turns as ``[{"role": ..., "content": ...}]``.

        Yields
        ------
        str
            Incremental text chunks from the streaming response.
        """
