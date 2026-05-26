"""Domain data models.

문서 트리(`document`), 블록 수준 편집(`edit`), 섹션 트리 액션(`outline`)으로
나뉘어 있으며, 호출 측은 이 패키지에서 평탄하게 임포트하면 된다.

    from core.data import Document, Edit, OutlineAction
"""
from .document import Block, Document, Section, SectionMeta
from .edit import Edit, InsertEdit, LLMEdit, ReplaceEdit, RewriteEdit
from .outline import OutlineAction

__all__ = [
    # document
    "Block",
    "SectionMeta",
    "Section",
    "Document",
    # edit
    "LLMEdit",
    "RewriteEdit",
    "ReplaceEdit",
    "InsertEdit",
    "Edit",
    # outline
    "OutlineAction",
]
