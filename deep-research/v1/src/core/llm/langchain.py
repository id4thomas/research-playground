from typing import Any

from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI

from config import get_settings

settings = get_settings()

class LangChainChatModel:
    @classmethod
    def _get_model(cls, model_name: str) -> ChatOpenAI:
        return ChatOpenAI(
            model=model_name,
            base_url=settings.llm.base_url,
            api_key=settings.llm.api_key
        )
    
    @classmethod
    async def chat(
        cls,
        messages: list[dict],
        model_name: str,
        **chat_kwargs: Any,
    ) -> AIMessage:
        model = cls._get_model(model_name)
        response = await model.ainvoke(messages, **chat_kwargs)
        return response