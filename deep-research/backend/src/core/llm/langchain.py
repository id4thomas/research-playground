from typing import Any

from langchain_openai import ChatOpenAI

from config import get_settings

settings = get_settings()


class LangChainChatModel:
    """Returns a ChatOpenAI configured for the local OpenAI-compatible server."""

    @classmethod
    def get_model(cls, model_name: str, params: dict[str, Any] = None) -> ChatOpenAI:
        if params is None:
            params = dict()
            
        model = ChatOpenAI(
            model = model_name or settings.llm.model,
            base_url = settings.llm.base_url,
            api_key = settings.llm.api_key,
            **params
        )
        return model
