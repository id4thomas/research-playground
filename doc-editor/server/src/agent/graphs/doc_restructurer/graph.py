"""doc_restructurer agent — outline-only edits.

START → restructure → assemble → END
(컨텍스트 수집 불필요: outline만으로 충분)
"""
from typing import Annotated

from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage
from typing_extensions import TypedDict

from agent.base import BaseAgent
from agent.graphs.doc_assistant.states import FinalOutput
from agent.graphs.doc_restructurer.nodes.assemble import restructure_assemble_node
from agent.graphs.doc_restructurer.nodes.restructure import restructure_node
from agent.modules.restructure_generate import RestructureGenerateOutput
from core.data import Document


class RestructurerState(TypedDict, total=False):
    messages: Annotated[list[BaseMessage], add_messages]
    document: Document
    selected: list[str] | None
    restructure: RestructureGenerateOutput
    final: FinalOutput


def build_restructurer_graph() -> CompiledStateGraph:
    b = StateGraph(RestructurerState)
    b.add_node("restructure", restructure_node)
    b.add_node("assemble", restructure_assemble_node)
    b.add_edge(START, "restructure")
    b.add_edge("restructure", "assemble")
    b.add_edge("assemble", END)
    return b.compile()


class DocRestructurerAgent(BaseAgent):
    _name = "DocRestructurerAgent"

    def __init__(self) -> None:
        self._graph: CompiledStateGraph | None = None

    def compile_graph(self) -> CompiledStateGraph:
        if self._graph is None:
            self._graph = build_restructurer_graph()
        return self._graph

    async def invoke(self, state: dict) -> dict:
        return await self.compile_graph().ainvoke(state)
