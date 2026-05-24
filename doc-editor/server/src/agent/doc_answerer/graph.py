"""doc_answerer agent.

START → context_collector → answer → assemble → END
"""
from typing import Annotated

from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage
from typing_extensions import TypedDict

from agent.base import BaseAgent
from agent.doc_answerer.nodes.answer import answer_node
from agent.doc_answerer.nodes.assemble import answer_assemble_node
from agent.doc_assistant.states import FinalOutput
from agent.modules.answer_generate import AnswerGenerateOutput
from agent.modules.context_collect import ContextCollectOutput
from agent.modules.intent_classify import IntentClassifyOutput
from agent.nodes.context_collector import context_collector_node
from core.data import Document


class AnswererState(TypedDict, total=False):
    messages: Annotated[list[BaseMessage], add_messages]
    document: Document
    selected: list[str] | None
    intent_router: IntentClassifyOutput
    context: ContextCollectOutput
    answer: AnswerGenerateOutput
    final: FinalOutput


def build_answerer_graph() -> CompiledStateGraph:
    b = StateGraph(AnswererState)
    b.add_node("context_collector", context_collector_node)
    b.add_node("answer", answer_node)
    b.add_node("assemble", answer_assemble_node)
    b.add_edge(START, "context_collector")
    b.add_edge("context_collector", "answer")
    b.add_edge("answer", "assemble")
    b.add_edge("assemble", END)
    return b.compile()


class DocAnswererAgent(BaseAgent):
    _name = "DocAnswererAgent"

    def __init__(self) -> None:
        self._graph: CompiledStateGraph | None = None

    def compile_graph(self) -> CompiledStateGraph:
        if self._graph is None:
            self._graph = build_answerer_graph()
        return self._graph

    async def invoke(self, state: dict) -> dict:
        return await self.compile_graph().ainvoke(state)
