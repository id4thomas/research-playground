"""Agent state for the doc-editor graph."""
from typing import Annotated

from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

from agent.modules.answer_generate import AnswerGenerateOutput as AnswerOutput
from agent.modules.clarify_generate import ClarifyGenerateOutput as ClarifyOutput
from agent.modules.context_collect import ContextCollectOutput
from agent.modules.edit_generate import EditGenerateOutput as EditOutput
from agent.modules.intent_classify import IntentClassifyOutput as IntentRouterOutput
from agent.modules.restructure_generate import RestructureGenerateOutput as RestructureOutput
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

    intent_router: IntentRouterOutput
    context: ContextCollectOutput
    edit: EditOutput
    restructure: RestructureOutput
    answer: AnswerOutput
    clarify: ClarifyOutput
    final: FinalOutput
