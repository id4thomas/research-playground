"""Domain data models.

문서 트리(`document`), 문서 편집 페이로드(`edit` — 블록/outline 수준), 그리고
프론트엔드와 주고받는 chat wire 스펙(`chat`)으로 나뉜다. 호출 측은 이 패키지에서
평탄하게 임포트하면 된다.

    from core.data import Document, BlockEdit, OutlineEdit
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
from .edit import (
    AddOutlineEdit,
    BlockEdit,
    InsertBlockEdit,
    MergeOutlineEdit,
    OutlineEdit,
    RemoveOutlineEdit,
    RenameOutlineEdit,
    ReplaceBlockEdit,
    RewriteBlockEdit,
)
from .chat import (
    BaseChatMessage,
    BaseInteraction,
    BlockInteraction,
    ChatMessage,
    ChatMessageAdapter,
    ClarifyChatMessage,
    Interaction,
    InteractionAdapter,
    InteractionChatMessage,
    OptionReplyChatMessage,
    OutlineInteraction,
)

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
    # edit (정규 블록 edit 페이로드)
    "RewriteBlockEdit",
    "ReplaceBlockEdit",
    "InsertBlockEdit",
    "BlockEdit",
    # outline edit (섹션 트리 변경)
    "RenameOutlineEdit",
    "AddOutlineEdit",
    "RemoveOutlineEdit",
    "MergeOutlineEdit",
    "OutlineEdit",
    # chat (wire: 프론트엔드 ↔ 서버)
    "ChatMessage",
    "BaseChatMessage",
    "InteractionChatMessage",
    "ClarifyChatMessage",
    "OptionReplyChatMessage",
    "BaseInteraction",
    "BlockInteraction",
    "OutlineInteraction",
    "Interaction",
    "ChatMessageAdapter",
    "InteractionAdapter",
]
