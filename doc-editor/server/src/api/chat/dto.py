from typing import Literal

from pydantic import BaseModel, Field

from core.data import Document, Edit, OutlineAction

__all__ = ["ChatMessage", "ChatRequest", "ChatResponse"]


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class ChatRequest(BaseModel):
    project_id: str
    messages: list[ChatMessage]
    document: Document
    selected: list[str] | None = None


class ChatResponse(BaseModel):
    message: ChatMessage
    edits: dict[str, list[Edit]] = Field(default_factory=dict)
    outline_actions: list[OutlineAction] = Field(default_factory=list)
    intent: str = ""
    suggest_new_session: bool = False
    suggest_new_session_reason: str | None = None
    clarify_options: list[str] = Field(default_factory=list)
