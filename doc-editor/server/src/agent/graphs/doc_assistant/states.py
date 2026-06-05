"""Shared agent state for the doc-editor graphs."""
from typing import Annotated

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field
from typing_extensions import TypedDict

from agent.operations import (
    AnswerGenerateOutput,
    ClarifyGenerateOutput,
    ContextCollectOutput,
    BlockEditGenerateOutput,
    IntentClassifyOutput,
    OutlineEditGenerateOutput,
)
from core.data import BlockEdit, Document, OutlineEdit


class FinalOutput(BaseModel):
    message: str = ""
    edits: dict[str, list[BlockEdit]] = Field(default_factory=dict)
    outline_edits: list[OutlineEdit] = Field(default_factory=list)
    clarify_options: list[str] = Field(default_factory=list)


class AgentState(TypedDict, total=False):
    messages: Annotated[list[BaseMessage], add_messages]
    document: Document
    selected: list[str] | None

    intent_router: IntentClassifyOutput
    context: ContextCollectOutput
    edit: BlockEditGenerateOutput
    restructure: OutlineEditGenerateOutput
    answer: AnswerGenerateOutput
    clarify: ClarifyGenerateOutput
    final: FinalOutput
