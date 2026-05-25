"""Chat endpoint DTOs.

ChatMessage 는 단순 텍스트가 아닌, 어시스턴트가 직전 턴에 어떤 intent로 무엇을
제안했고 사용자가 어떻게 반응했는지 메타데이터를 함께 담는다. 서버는
`to_lc_messages` 에서 이 메타데이터를 [ASSISTANT · ...] / [USER · 선택지 ① 채택]
같은 태그가 붙은 텍스트 본문으로 직렬화하여 LLM에 넘긴다.
"""
from typing import Literal

from pydantic import BaseModel, Field

from core.data import Document, Edit, OutlineAction
from core.langchain.usage import TokenUsage

__all__ = [
    "ChatMessage",
    "ChatRequest",
    "ChatResponse",
    "EditProposalMeta",
    "OutlineProposalMeta",
]


class EditProposalMeta(BaseModel):
    """어시스턴트가 제안했던 블록 수정 항목 + 사용자 결정."""
    ref: str
    action: Literal["REWRITE", "REPLACE", "INSERT"]
    target_desc: str = ""  # 위치 설명 (예: "'배경' 섹션 1번째 블록 (S1;0)")
    summary: str = ""      # LLM이 적은 변경 의도/한줄 요약
    content: str = ""      # 변경 내용 본문 (REWRITE=새 본문, REPLACE="\"X\" → \"Y\"", INSERT=새 블록 본문)
    status: Literal["pending", "accepted", "declined", "instructed"] = "pending"
    instruction: str | None = None


class OutlineProposalMeta(BaseModel):
    """어시스턴트가 제안했던 섹션 구조 변경 + 사용자 결정."""
    action: Literal["RENAME", "ADD", "REMOVE", "MERGE"]
    target_desc: str = ""
    summary: str = ""
    status: Literal["pending", "accepted", "declined", "instructed"] = "pending"
    instruction: str | None = None


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str
    # --- assistant 턴 메타데이터 ---
    intent: Literal["edit", "clarify", "answer", "restructure"] | None = None
    clarify_options: list[str] | None = None
    edit_proposals: list[EditProposalMeta] | None = None
    outline_proposals: list[OutlineProposalMeta] | None = None
    # --- user 턴 메타데이터 ---
    # 직전 어시스턴트 clarify 선택지 중 몇 번째를 골랐는지(0-base). None = 직접 입력.
    picked_option_index: int | None = None


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
    token_usage: TokenUsage = Field(default_factory=TokenUsage)
