import logging
from abc import ABC, abstractmethod
from typing import Any, Generic, Literal, Optional, TypedDict, TypeVar

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph
from langchain_openai import ChatOpenAI
from langgraph.types import Command
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion
from pydantic import BaseModel

from config import get_settings
from core.llm.token_usage import TokenUsage

settings = get_settings()


StateT = TypeVar("StateT", bound=dict[str, Any])
NodeReturn = dict[str, Any] | Command

class OperationResult[T](BaseModel):
    data: Optional[T] = None
    token_usage: Optional[TokenUsage] = None


class BaseOperation(ABC):
    """Stateless operation to be re-used in nodes"""

    @classmethod
    @abstractmethod
    async def run(cls, *args, **kwargs) -> OperationResult:
        raise NotImplementedError

class BaseLLMOperation(BaseOperation):
    @classmethod
    def _init_client(cls) -> AsyncOpenAI:
        return AsyncOpenAI(base_url=settings.llm.base_url, api_key=settings.llm.api_key)

    # @classmethod
    # async def chat(
    #     cls,
    #     model: ChatOpenAI,
    #     messages: list[dict],
    #     json_schema: dict[str, Any]| None = None
    # ) -> AIMessage:
    #     if json_schema is None:
    #         result = await model.ainvoke(messages)
    #     else:
    #         result = await model.with_structured_output(
    #             json_schema,
    #             method="json_schema",
    #             include_raw=True
    #         ).ainvoke(messages)
            
    #         # get AIMessage, include_raw returns {"raw": AIMessage(...). "parsed": dict, "parsing_error": None}
    #         result = result["raw"]
    #     return result

    @classmethod
    async def chat(
        cls, model: str, messages: list[dict], params: Optional[dict] = None, response_format: Optional[dict] = None
    ) -> ChatCompletion:
        client = cls._init_client()
        if params is None:
            params = dict()

        # response = await client.chat.completions.parse(
        response = await client.chat.completions.create(
            messages=messages, model=model, response_format=response_format, **params
        )
        return response

class BaseNode(ABC, Generic[StateT]):
    """LangGraph-compatible node.

    Subclasses implement `run(state, config)` and may return either a partial
    state patch (merged via the state's reducers) or a `Command` for routing.
    Instances are callable and can be passed directly to `StateGraph.add_node`.
    """

    name: str = "BaseNode"

    def __init__(self) -> None:
        self._logger = logging.getLogger(f"agent.node.{self.name}")

    async def __call__(
        self,
        state: StateT,
        config: RunnableConfig | None = None,
    ) -> NodeReturn:
        """
        RunnableConfig: https://reference.langchain.com/python/langchain-core/runnables/config/RunnableConfig
        """

        try:
            out = await self.run(state, config or {})
        except Exception as e:
            self._logger.exception(f"node failed: {str(e)}")
            return self.on_error(state, e)
        return out

    @abstractmethod
    async def run(self, state: StateT, config: RunnableConfig) -> NodeReturn:
        raise NotImplementedError
    
    def on_error(self, state: StateT, err: Exception) -> NodeReturn:
        """Default: re-raise so LangGraph's retry/error policy handles it.

        Override to record the error into state or return a routing `Command`.
        """
        raise err
