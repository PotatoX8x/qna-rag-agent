import backoff
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from pydantic import BaseModel

from app.models.llm_client.base import BaseLLMClient


def _build_messages(system_prompt: str, user_prompt: str, messages: list[dict] | None = None) -> list:
    """Assemble a LangChain message list from prompt parts and optional history.

    Parameters
    ----------
    system_prompt : str
        Always placed first as a ``SystemMessage``.
    user_prompt : str
        Appended as the final ``HumanMessage`` when ``messages`` is ``None``.
    messages : list[dict] or None, optional
        Prior turns as ``[{"role": "user"|"assistant", "content": str}]``.
        When provided, ``user_prompt`` is ignored in favour of the history tail.

    Returns
    -------
    list
        Ordered list of LangChain message objects ready to pass to ``ainvoke``.
    """
    msgs = [SystemMessage(content=system_prompt)]
    if messages:
        for m in messages:
            if m["role"] == "user":
                msgs.append(HumanMessage(content=m["content"]))
            elif m["role"] == "assistant":
                msgs.append(AIMessage(content=m["content"]))
    else:
        msgs.append(HumanMessage(content=user_prompt))
    return msgs


class LangChainLLMClient(BaseLLMClient):
    """``BaseLLMClient`` backed by any LangChain chat model, with a lighter model for streaming."""

    def __init__(self, model: BaseChatModel, model_fast: BaseChatModel | None = None):
        """
        Parameters
        ----------
        model : BaseChatModel
            Primary model used for completions and structured output.
        model_fast : BaseChatModel or None, optional
            Lighter model used for streaming. Falls back to ``model`` when ``None``.
        """
        self._model = model
        self._model_fast = model_fast or model

    @backoff.on_exception(backoff.expo, Exception, max_tries=3)
    async def complete(self, system_prompt, user_prompt, temperature=0.4, max_tokens=None) -> str:
        """Return a plain-text completion with exponential-backoff retries.

        Parameters
        ----------
        system_prompt : str
            Instruction context.
        user_prompt : str
            The user's message.
        temperature : float, optional
            Sampling temperature. Default is 0.4.
        max_tokens : int or None, optional
            Hard cap on output tokens.

        Returns
        -------
        str
            Full response text.
        """
        response = await self._model.ainvoke(_build_messages(system_prompt, user_prompt))
        return response.content

    @backoff.on_exception(backoff.expo, Exception, max_tries=3)
    async def complete_structured(self, system_prompt, user_prompt, schema, messages=None):
        """Return a validated Pydantic model via structured output with retries.

        Parameters
        ----------
        system_prompt : str
            Instruction context.
        user_prompt : str
            The user's message.
        schema : type[BaseModel]
            Pydantic model the response must conform to.
        messages : list[dict] or None, optional
            Prior conversation turns.

        Returns
        -------
        BaseModel
            Parsed and validated instance of ``schema``.
        """
        structured = self._model.with_structured_output(schema)
        return await structured.ainvoke(_build_messages(system_prompt, user_prompt, messages))

    async def stream(self, system_prompt, user_prompt, messages=None):
        """Yield response text deltas from the fast model.

        Parameters
        ----------
        system_prompt : str
            Instruction context.
        user_prompt : str
            The user's message.
        messages : list[dict] or None, optional
            Prior conversation turns.

        Yields
        ------
        str
            Incremental text chunks.
        """
        async for chunk in self._model_fast.astream(_build_messages(system_prompt, user_prompt, messages)):
            if chunk.content:
                yield chunk.content
