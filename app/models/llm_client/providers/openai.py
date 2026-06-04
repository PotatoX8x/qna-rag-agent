from langchain_openai import ChatOpenAI

from app.models.llm_client.langchain_base import LangChainLLMClient
from app.models.llm_client.registry import LLMRegistry


@LLMRegistry.register("openai")
class OpenAILLMClient(LangChainLLMClient):
    def __init__(self, cfg: dict):
        timeout = cfg.get("timeout", 30)
        max_retries = cfg.get("max_retries", 2)
        model = ChatOpenAI(
            model=cfg["model"],
            api_key=cfg["api_key"],
            temperature=0.4,
            timeout=timeout,
            max_retries=max_retries,
        )
        model_fast = ChatOpenAI(
            model=cfg.get("model_fast", cfg["model"]),
            api_key=cfg["api_key"],
            temperature=0.5,
            timeout=timeout,
            max_retries=max_retries,
        )
        super().__init__(model=model, model_fast=model_fast)
