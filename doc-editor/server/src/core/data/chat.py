"""Chat 히스토리 명세 — **wire 스펙** (프론트엔드 ↔ 서버).

이 모듈은 프론트엔드와 서버가 주고받는 메시지 표현이다. LLM에 직접 넘기는 메시지
표현(role/content 텍스트)과는 분리되어 있다 (그쪽은 `agent.base.LLMChatMessage`).

설계 의도:
  - 기존 히스토리는 ref를 `"S1;0"`(섹션코드;인덱스)로 표현해, 편집이 누적되면
    인덱스가 어긋나 추적이 어려웠다. 여기서는 액션이 블록 **UUID**(`ref`)를 가리킨다.
  - "사용자/어시스턴트가 무엇을 했는지"를 단순 텍스트가 아니라 구조화된
    `InteractionAction` 으로 담아 정보량을 높이고, 프론트엔드가 그대로 반영/리플레이한다.

계층:
  ChatMessage (type 디스크리미네이터)
  ├─ BaseChatMessage         : 단순 텍스트 (+ clarify 선택지 등 메타)
  └─ InteractionChatMessage  : 텍스트 + 구조화된 actions[]

  InteractionAction (scope 디스크리미네이터)
  ├─ BlockAction   (REWRITE / REPLACE / INSERT)   — 블록 본문 수정 (ref=블록 UUID)
  └─ OutlineAction (ADD / MERGE / RENAME / REMOVE) — 섹션 구조 변경 (ref=섹션 code)
"""
from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field, TypeAdapter

from core.data.document import Block

__all__ = [
    "BlockAction",
    "OutlineAction",
    "InteractionAction",
    "BaseChatMessage",
    "InteractionChatMessage",
    "ClarifyChatMessage",
    "OptionReplyChatMessage",
    "ChatMessage",
    "ChatMessageAdapter",
    "InteractionActionAdapter",
]


# ---------------------------------------------------------------------------
# Interaction actions — "무엇을 했는지" 구조화
# ---------------------------------------------------------------------------
class BaseInteractionAction(BaseModel):
    # pending: 제안만 함 / accepted: 사용자 수락 / declined: 거절 / instructed: 직접 지시
    status: Literal["pending", "accepted", "declined", "instructed"] = "pending"
    summary: str = Field("", description="이 액션이 무엇을 어떻게 바꾸는지 한국어 1줄 요약.")
    target_desc: str = Field("", description="사람이 읽을 대상 설명 (예: \"'배경' 섹션 1번째 블록\").")
    instruction: str | None = Field(None, description="status=instructed 일 때 사용자의 직접 지시문.")


# --- Block scope ---
class BaseBlockAction(BaseInteractionAction):
    scope: Literal["block"] = "block"
    ref: str = Field(..., description="대상 블록 id (UUID). INSERT는 기준(앵커) 블록 id.")


class RewriteBlockAction(BaseBlockAction):
    action: Literal["REWRITE"] = "REWRITE"
    block: Block


class ReplaceBlockAction(BaseBlockAction):
    action: Literal["REPLACE"] = "REPLACE"
    source: str
    target: str


class InsertBlockAction(BaseBlockAction):
    action: Literal["INSERT"] = "INSERT"
    block: Block


BlockAction = Annotated[
    Union[RewriteBlockAction, ReplaceBlockAction, InsertBlockAction],
    Field(discriminator="action"),
]


# --- Outline scope ---
class BaseOutlineAction(BaseInteractionAction):
    scope: Literal["outline"] = "outline"
    ref: str | None = Field(None, description="대상 섹션 code (ADD는 부모 code, None=루트).")


class AddOutlineAction(BaseOutlineAction):
    action: Literal["ADD"] = "ADD"
    title: str = ""
    level: int | None = None
    position: int | None = None


class MergeOutlineAction(BaseOutlineAction):
    action: Literal["MERGE"] = "MERGE"
    targets: list[str] = Field(default_factory=list)
    title: str | None = None
    level: int | None = None


class RenameOutlineAction(BaseOutlineAction):
    action: Literal["RENAME"] = "RENAME"
    title: str = ""


class RemoveOutlineAction(BaseOutlineAction):
    action: Literal["REMOVE"] = "REMOVE"


OutlineAction = Annotated[
    Union[AddOutlineAction, MergeOutlineAction, RenameOutlineAction, RemoveOutlineAction],
    Field(discriminator="action"),
]


InteractionAction = Annotated[
    Union[BlockAction, OutlineAction],
    Field(discriminator="scope"),
]

InteractionActionAdapter: TypeAdapter[InteractionAction] = TypeAdapter(InteractionAction)


# ---------------------------------------------------------------------------
# Chat messages (wire)
# ---------------------------------------------------------------------------
# 메시지 종류는 `type` 하나로만 구분한다(별도 intent 필드 없음):
#   base(=answer/일반) · interaction(edit/restructure, action scope로 구분) · clarify · option_reply
class BaseChatMessage(BaseModel):
    """단순 텍스트 메시지. role/content 만 갖는다."""
    type: Literal["base"] = "base"
    role: Literal["user", "assistant", "system"] = "user"
    content: str = Field("", description="대표 메시지 본문.")


class InteractionChatMessage(BaseChatMessage):
    """문서 수정이 동반된 (assistant) 메시지 — 텍스트 + 구조화된 actions."""
    type: Literal["interaction"] = "interaction"  # type: ignore[assignment]
    actions: list[InteractionAction] = Field(default_factory=list)


class ClarifyChatMessage(BaseChatMessage):
    """assistant가 사용자에게 선택지를 제시하는 메시지."""
    type: Literal["clarify"] = "clarify"  # type: ignore[assignment]
    role: Literal["user", "assistant", "system"] = "assistant"
    clarify_options: list[str] = Field(default_factory=list, description="제시한 선택지 목록.")


class OptionReplyChatMessage(BaseChatMessage):
    """user가 직전 clarify 선택지 중 하나를 고른 메시지."""
    type: Literal["option_reply"] = "option_reply"  # type: ignore[assignment]
    role: Literal["user", "assistant", "system"] = "user"
    picked_option_index: int = Field(..., description="고른 선택지 인덱스(0-base).")


ChatMessage = Annotated[
    Union[
        BaseChatMessage,
        InteractionChatMessage,
        ClarifyChatMessage,
        OptionReplyChatMessage,
    ],
    Field(discriminator="type"),
]

ChatMessageAdapter: TypeAdapter[ChatMessage] = TypeAdapter(ChatMessage)
