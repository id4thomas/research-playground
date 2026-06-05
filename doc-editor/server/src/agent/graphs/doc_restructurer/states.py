"""State schema for the doc_restructurer subgraph."""
from typing import Annotated

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from agent.graphs.doc_assistant.states import FinalOutput
from agent.operations import OutlineEditGenerateOutput
from core.data import Document


class RestructurerState(TypedDict, total=False):
    messages: Annotated[list[BaseMessage], add_messages]
    document: Document
    selected: list[str] | None
    restructure: OutlineEditGenerateOutput
    final: FinalOutput
