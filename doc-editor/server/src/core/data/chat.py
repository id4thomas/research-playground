"""Chat 히스토리 명세 — **wire 스펙** (프론트엔드 ↔ 서버).

이 모듈은 프론트엔드와 서버가 주고받는 메시지 표현이다. LLM에 직접 넘기는 메시지
표현(role/content 텍스트)과는 분리되어 있다 (그쪽은 `agent.base.LLMChatMessage`).

설계 의도:
  - 기존 히스토리는 ref를 `"S1;0"`(섹션코드;인덱스)로 표현해, 편집이 누적되면
    인덱스가 어긋나 추적이 어려웠다. 여기서는 상호작용이 블록 **UUID**(`ref`)를 가리킨다.
  - "사용자/어시스턴트가 무엇을 했는지"를 단순 텍스트가 아니라 구조화된
    `Interaction` 으로 담아 정보량을 높이고, 프론트엔드가 그대로 반영/리플레이한다.

명명: "무엇을 했는지"의 한 단위는 `Interaction`(상호작용)이고, 그 안의 "무엇을 어떻게
바꾸는가"(op + 페이로드)는 **재사용된 도메인 모델**(`core.data.edit.BlockEdit` /
`core.data.edit.OutlineEdit`)을 합성해 담는다. 이렇게 하면 op 종류를 가리키는
`action` 필드가 `BlockEdit`/`OutlineEdit` 한 곳에만 존재해 의미 충돌이 없다.

계층:
  ChatMessage (type 디스크리미네이터)
  ├─ BaseChatMessage         : 단순 텍스트 (+ clarify 선택지 등 메타)
  └─ InteractionChatMessage  : 텍스트 + 구조화된 interactions[]

  Interaction (scope 디스크리미네이터) = 상호작용 메타(status/summary/target_desc) +
  ├─ BlockInteraction   (ref=블록 UUID, edit: BlockEdit)       — 블록 본문 수정
  └─ OutlineInteraction (outline: OutlineEdit)                 — 섹션 구조 변경
"""
from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field, TypeAdapter

from core.data.edit import BlockEdit, OutlineEdit

__all__ = [
    "BaseInteraction",
    "BlockInteraction",
    "OutlineInteraction",
    "Interaction",
    "BaseChatMessage",
    "InteractionChatMessage",
    "ClarifyChatMessage",
    "OptionReplyChatMessage",
    "ChatMessage",
    "ChatMessageAdapter",
    "InteractionAdapter",
]


# ---------------------------------------------------------------------------
# Interaction — "무엇을 했는지" 구조화 (상호작용 메타 + 재사용된 도메인 페이로드)
# ---------------------------------------------------------------------------
class BaseInteraction(BaseModel):
    # pending: 제안만 함 / accepted: 사용자 수락 / declined: 거절 / instructed: 직접 지시
    status: Literal["pending", "accepted", "declined", "instructed"] = "pending"
    summary: str = Field("", description="이 상호작용이 무엇을 어떻게 바꾸는지 한국어 1줄 요약.")
    target_desc: str = Field("", description="사람이 읽을 대상 설명 (예: \"'배경' 섹션 1번째 블록\").")
    instruction: str | None = Field(None, description="status=instructed 일 때 사용자의 직접 지시문.")


class BlockInteraction(BaseInteraction):
    """블록 본문 수정 상호작용. `edit` 가 무엇을 어떻게 바꾸는지 담는다."""
    scope: Literal["block"] = "block"
    ref: str = Field(..., description="대상 블록 id (UUID). INSERT는 기준(앵커) 블록 id.")
    edit: BlockEdit


class OutlineInteraction(BaseInteraction):
    """섹션 구조 변경 상호작용. `outline` 이 대상 섹션 code/op 를 담는다."""
    scope: Literal["outline"] = "outline"
    outline: OutlineEdit


Interaction = Annotated[
    Union[BlockInteraction, OutlineInteraction],
    Field(discriminator="scope"),
]

InteractionAdapter: TypeAdapter[Interaction] = TypeAdapter(Interaction)


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
    """문서 수정이 동반된 (assistant) 메시지 — 텍스트 + 구조화된 interactions."""
    type: Literal["interaction"] = "interaction"  # type: ignore[assignment]
    interactions: list[Interaction] = Field(default_factory=list)


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
