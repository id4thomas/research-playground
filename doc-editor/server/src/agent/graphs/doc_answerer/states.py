"""State schema for the doc_answerer subgraph."""
from typing import Annotated

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from agent.graphs.doc_assistant.states import FinalOutput
from agent.operations import AnswerGenerateOutput, ContextCollectOutput
from core.data import Document


class AnswererState(TypedDict, total=False):
    messages: Annotated[list[BaseMessage], add_messages]
    document: Document
    selected: list[str] | None
    hint_sections: list[str] | None  # optional target-section hint from caller
    context: ContextCollectOutput
    answer: AnswerGenerateOutput
    final: FinalOutput
