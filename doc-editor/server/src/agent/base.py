"""Hierarchy: Agent (Graph) > Node > Operation"""
from abc import ABC, abstractmethod
from typing import Any, Generic, Literal, TypedDict, TypeVar

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph
from langchain_openai import ChatOpenAI
from langgraph.types import Command

from core.langchain.llm import LangChainChatModel
from core.langchain.usage import TokenUsage
from core.logger import get_logger
from core.prompt.loader import get_prompt_loader
from core.prompt.model import PromptTemplate, GenerationConfig
from core.prompts import HISTORY_FORMAT_NOTE

StateT = TypeVar("StateT", bound=dict[str, Any])
NodeReturn = dict[str, Any] | Command


class ChatMessage(TypedDict):
    """A single chat turn passed to an Operation as LLM context.

    Plain dict (no LangChain classes) so Operations stay framework-agnostic.
    `role` is the speaker; `content` is the text shown to the model.
    """

    role: Literal["system", "developer", "user", "assistant"]
    content: str


_ROLE_LABELS = {"system": "시스템", "developer": "시스템", "user": "사용자", "assistant": "어시스턴트"}


def format_history(history: list[ChatMessage] | None) -> str:
    """Render chat turns into a single text block for prompt injection.

    Operations feed this into a `history_text` template variable instead of
    passing raw messages to the model, so the prompt controls how prior
    context is framed. The tag-format explainer (HISTORY_FORMAT_NOTE) is
    bundled here next to the turns it describes, rather than in the system
    prompt — and is omitted entirely when there is no history.
    """
    if not history:
        return "(이전 대화 없음)"
    body = "\n".join(
        f"[{_ROLE_LABELS.get(m['role'], m['role'])}] {m['content']}" for m in history
    )
    return HISTORY_FORMAT_NOTE + "\n" + body


_LC_TYPE_TO_ROLE = {"human": "user", "ai": "assistant", "system": "system", "tool": "assistant"}


def split_instruction_history(messages: list) -> tuple[str, list[ChatMessage]]:
    """Split a chat message list into (latest instruction, prior history).

    Bridges graph state (LangChain `BaseMessage` list) and Operations (which
    take an explicit `instruction` string + `history` dicts). The final turn's
    text becomes the instruction to act on; earlier turns become history.
    """
    if not messages:
        return "", []
    *prior, last = messages
    instruction = getattr(last, "content", "") or ""
    history = [
        ChatMessage(
            role=_LC_TYPE_TO_ROLE.get(getattr(m, "type", "user"), "user"),
            content=getattr(m, "content", "") or "",
        )
        for m in prior
    ]
    return instruction, history


class BaseAgent(ABC):
    """Base agent interface."""
    _name: str = "BaseAgent"

    @abstractmethod
    def compile_graph(self) -> CompiledStateGraph:
        raise NotImplementedError()

    @abstractmethod
    async def invoke(self, state: dict) -> dict:
        raise NotImplementedError()
    
class BaseNode(ABC, Generic[StateT]):
    """LangGraph-compatible node.

    Subclasses implement `run(state, config)` and may return either a partial
    state patch (merged via the state's reducers) or a `Command` for routing.
    Instances are callable and can be passed directly to `StateGraph.add_node`.
    """

    name: str = "BaseNode"

    def __init__(self) -> None:
        self._logger = get_logger(f"node.{self.name}")

    async def __call__(
        self,
        state: StateT,
        config: RunnableConfig | None = None,
    ) -> NodeReturn:
        """
        RunnableConfig: https://reference.langchain.com/python/langchain-core/runnables/config/RunnableConfig
        """
        
        self._logger.debug("enter")
        try:
            out = await self.run(state, config or {})
        except Exception as e:
            self._logger.exception("node failed: %s", e)
            return self.on_error(state, e)
        if isinstance(out, Command):
            self._logger.debug("exit command goto=%s", out.goto)
        else:
            self._logger.debug("exit keys=%s", list(out.keys()))
        return out

    @abstractmethod
    async def run(self, state: StateT, config: RunnableConfig) -> NodeReturn:
        raise NotImplementedError

    def on_error(self, state: StateT, err: Exception) -> NodeReturn:
        """Default: re-raise so LangGraph's retry/error policy handles it.

        Override to record the error into state or return a routing `Command`.
        """
        raise err


class BaseOperation(ABC):
    """Stateless operation to be re-used in nodes"""

    @classmethod
    @abstractmethod
    async def run(cls, *args, **kwargs):
        raise NotImplementedError
    

class BaseLLMOperation(BaseOperation):
    @classmethod
    def _load_prompt(cls, name: str) -> PromptTemplate:
        template = get_prompt_loader().load(name)
        return template
    
    @classmethod
    def _load_model(cls, config: GenerationConfig) -> ChatOpenAI:
        model = LangChainChatModel.get_model(
            model_name=config.model_name,
            params=config.parameters
        )
        return model
    
    @classmethod
    async def generate(
        cls,
        model: ChatOpenAI,
        messages: list[dict],
        json_schema: dict[str, Any]| None = None
    ) -> AIMessage:
        if json_schema is None:
            result = await model.ainvoke(messages)
        else:
            result = await model.with_structured_output(
                json_schema,
                method="json_schema",
                include_raw=True
            ).ainvoke(messages)
            
            # get AIMessage, include_raw returns {"raw": AIMessage(...). "parsed": dict, "parsing_error": None}
            result = result["raw"]
        return result
    
    @classmethod
    def parse_token_usage(cls, msg: AIMessage) -> TokenUsage:
        return TokenUsage.from_message(msg)
        