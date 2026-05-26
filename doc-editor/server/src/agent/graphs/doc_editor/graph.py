"""doc_editor agent — single-action edit graph.

START → context_collector → edit → assemble → END
"""
from typing import Annotated

from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage
from typing_extensions import TypedDict

from agent.base import BaseAgent
from agent.graphs.doc_assistant.states import FinalOutput
from agent.graphs.doc_editor.nodes.assemble import edit_assemble_node
from agent.graphs.doc_editor.nodes.edit import edit_node
from agent.modules.context_collect import ContextCollectOutput
from agent.modules.edit_generate import EditGenerateOutput
from agent.modules.intent_classify import IntentClassifyOutput
from agent.nodes.context_collector import context_collector_node
from core.data import Document


class EditorState(TypedDict, total=False):
    messages: Annotated[list[BaseMessage], add_messages]
    document: Document
    selected: list[str] | None
    intent_router: IntentClassifyOutput
    context: ContextCollectOutput
    edit: EditGenerateOutput
    final: FinalOutput


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
