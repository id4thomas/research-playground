"""Chat endpoint DTOs (wire 스펙).

요청/응답 모두 `core.data.chat` 의 wire 메시지 스펙을 사용한다. 어시스턴트가 제안한
문서 변경은 응답 메시지의 구조화된 `actions[]`(블록 UUID 참조) 로 전달되며, 프론트엔드는
이를 그대로 반영/리플레이한다. LLM에 넘기는 메시지 표현과는 분리돼 있다
(`agent.base.LLMChatMessage` + `api.chat.serialize`).
"""
from pydantic import BaseModel, Field

from core.data import Document
from core.data.chat import ChatMessage
from core.langchain.usage import TokenUsage

__all__ = ["ChatRequest", "ChatResponse"]


class ChatRequest(BaseModel):
    project_id: str
    messages: list[ChatMessage]
    document: Document
    selected: list[str] | None = None


class ChatResponse(BaseModel):
    # 어시스턴트 응답 메시지. 행위 구분은 message.type 으로만 한다(별도 intent 없음):
    # base(answer) · interaction(edit/restructure, interaction scope) · clarify.
    # 제안된 문서 변경은 InteractionChatMessage.interactions 에 담긴다.
    message: ChatMessage
    suggest_new_session: bool = False
    suggest_new_session_reason: str | None = None
    token_usage: TokenUsage = Field(default_factory=TokenUsage)
