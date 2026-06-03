"""doc_editor agent — single-action edit graph.

START → context_collector → edit → assemble → END
"""
from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph

from agent.base import BaseAgent
from agent.graphs.doc_editor.nodes.assemble import edit_assemble_node
from agent.graphs.doc_editor.nodes.context_collector import context_collector_node
from agent.graphs.doc_editor.nodes.edit import edit_node
from agent.graphs.doc_editor.states import EditorState


def build_editor_graph() -> CompiledStateGraph:
    b = StateGraph(EditorState)
    b.add_node("context_collector", context_collector_node)
    b.add_node("edit", edit_node)
    b.add_node("assemble", edit_assemble_node)
    b.add_edge(START, "context_collector")
    b.add_edge("context_collector", "edit")
    b.add_edge("edit", "assemble")
    b.add_edge("assemble", END)
    return b.compile()


class DocEditorAgent(BaseAgent):
    _name = "DocEditorAgent"

    def __init__(self) -> None:
        self._graph: CompiledStateGraph | None = None

    def compile_graph(self) -> CompiledStateGraph:
        if self._graph is None:
            self._graph = build_editor_graph()
        return self._graph

    async def invoke(self, state: dict) -> dict:
        return await self.compile_graph().ainvoke(state)
