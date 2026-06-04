import backoff
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from pydantic import BaseModel

from app.models.llm_client.base import BaseLLMClient


def _build_messages(system_prompt: str, user_prompt: str, messages: list[dict] | None = None) -> list:
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
    """BaseLLMClient backed by any LangChain chat model, with a lighter model for streaming."""

    def __init__(self, model: BaseChatModel, model_fast: BaseChatModel | None = None):
        self._model = model
        self._model_fast = model_fast or model

    @backoff.on_exception(backoff.expo, Exception, max_tries=3)
    async def complete(self, system_prompt, user_prompt, temperature=0.4, max_tokens=None) -> str:
        response = await self._model.ainvoke(_build_messages(system_prompt, user_prompt))
        return response.content

    @backoff.on_exception(backoff.expo, Exception, max_tries=3)
    async def complete_structured(self, system_prompt, user_prompt, schema, messages=None):
        structured = self._model.with_structured_output(schema)
        return await structured.ainvoke(_build_messages(system_prompt, user_prompt, messages))

    async def stream(self, system_prompt, user_prompt, messages=None):
        async for chunk in self._model_fast.astream(_build_messages(system_prompt, user_prompt, messages)):
            if chunk.content:
                yield chunk.content
