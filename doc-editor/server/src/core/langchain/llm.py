from typing import Any

from langchain_openai import ChatOpenAI

from config import get_settings

settings = get_settings()


class LangChainChatModel:
    """Returns a ChatOpenAI configured for the local OpenAI-compatible server."""

    @classmethod
    def get_model(
        cls,
        model_name: str | None = None,
        temperature: float | None = None,
        max_completion_tokens: int | None = None,
        **kwargs: Any,
    ) -> ChatOpenAI:
        params: dict[str, Any] = {
            "model": model_name or settings.llm.model,
            "base_url": settings.llm.base_url,
            "api_key": settings.llm.api_key,
        }
        if temperature is not None:
            params["temperature"] = temperature
        if max_completion_tokens is not None:
            params["max_completion_tokens"] = max_completion_tokens
        params.update(kwargs)
        return ChatOpenAI(**params)
