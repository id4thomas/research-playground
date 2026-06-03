"""Domain data models.

문서 트리(`document`), 블록 수준 편집(`edit`), 섹션 트리 액션(`outline`), 그리고
프론트엔드와 주고받는 chat wire 스펙(`chat`)으로 나뉜다. 호출 측은 이 패키지에서
평탄하게 임포트하면 된다.

    from core.data import Document, Edit, OutlineAction
    from core.data import ChatMessage, InteractionChatMessage  # wire
"""
from .document import (
    Block,
    Document,
    EquationBlock,
    Section,
    SectionMeta,
    TableBlock,
    TextBlock,
    make_block,
    new_block_id,
)
from .edit import Edit, InsertEdit, LLMEdit, ReplaceEdit, RewriteEdit
from .outline import OutlineAction
from .chat import (
    BaseChatMessage,
    ChatMessage,
    ChatMessageAdapter,
    InteractionAction,
    InteractionActionAdapter,
    InteractionChatMessage,
)
from .chat import BlockAction as WireBlockAction
from .chat import OutlineAction as WireOutlineAction

__all__ = [
    # document
    "Block",
    "TextBlock",
    "TableBlock",
    "EquationBlock",
    "make_block",
    "new_block_id",
    "SectionMeta",
    "Section",
    "Document",
    # edit (LLM-facing internal)
    "LLMEdit",
    "RewriteEdit",
    "ReplaceEdit",
    "InsertEdit",
    "Edit",
    # outline (LLM-facing internal)
    "OutlineAction",
    # chat (wire: 프론트엔드 ↔ 서버)
    "ChatMessage",
    "BaseChatMessage",
    "InteractionChatMessage",
    "InteractionAction",
    "WireBlockAction",
    "WireOutlineAction",
    "ChatMessageAdapter",
    "InteractionActionAdapter",
]
