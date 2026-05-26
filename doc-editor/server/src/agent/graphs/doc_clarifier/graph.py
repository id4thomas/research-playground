"""doc_clarifier agent — generate clarifying question + clickable options.

START → clarify → assemble → END

intent_router는 더 이상 clarify 질문/보기를 만들지 않는다. doc_clarifier가
독립적인 LLM 호출로 question/options를 직접 생성한다.
"""
from typing import Annotated

from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage
from typing_extensions import TypedDict

from agent.base import BaseAgent
from agent.graphs.doc_assistant.states import FinalOutput
from agent.graphs.doc_clarifier.nodes.assemble import clarify_assemble_node
from agent.graphs.doc_clarifier.nodes.clarify import clarify_node
from agent.modules.clarify_generate import ClarifyGenerateOutput
from core.data import Document


class ClarifierState(TypedDict, total=False):
    messages: Annotated[list[BaseMessage], add_messages]
    document: Document
    selected: list[str] | None
    clarify: ClarifyGenerateOutput
    final: FinalOutput


def build_clarifier_graph() -> CompiledStateGraph:
    b = StateGraph(ClarifierState)
    b.add_node("clarify", clarify_node)
    b.add_node("assemble", clarify_assemble_node)
    b.add_edge(START, "clarify")
    b.add_edge("clarify", "assemble")
    b.add_edge("assemble", END)
    return b.compile()


class DocClarifierAgent(BaseAgent):
    _name = "DocClarifierAgent"

    def __init__(self) -> None:
        self._graph: CompiledStateGraph | None = None

    def compile_graph(self) -> CompiledStateGraph:
        if self._graph is None:
            self._graph = build_clarifier_graph()
        return self._graph

    async def invoke(self, state: dict) -> dict:
        return await self.compile_graph().ainvoke(state)
