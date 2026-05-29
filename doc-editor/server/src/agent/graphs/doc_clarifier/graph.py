"""doc_clarifier agent — generate clarifying question + clickable options.

START → clarify → assemble → END
"""
from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph

from agent.base import BaseAgent
from agent.graphs.doc_clarifier.nodes.assemble import clarify_assemble_node
from agent.graphs.doc_clarifier.nodes.clarify import clarify_node
from agent.graphs.doc_clarifier.states import ClarifierState


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
