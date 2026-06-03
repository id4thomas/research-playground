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
    EditGenerateOutput,
    IntentClassifyOutput,
    RestructureGenerateOutput,
)
from core.data import Document, Edit, OutlineAction


class FinalOutput(BaseModel):
    message: str = ""
    edits: dict[str, list[Edit]] = Field(default_factory=dict)
    outline_actions: list[OutlineAction] = Field(default_factory=list)
    clarify_options: list[str] = Field(default_factory=list)


class AgentState(TypedDict, total=False):
    messages: Annotated[list[BaseMessage], add_messages]
    document: Document
    selected: list[str] | None

    intent_router: IntentClassifyOutput
    context: ContextCollectOutput
    edit: EditGenerateOutput
    restructure: RestructureGenerateOutput
    answer: AnswerGenerateOutput
    clarify: ClarifyGenerateOutput
    final: FinalOutput
