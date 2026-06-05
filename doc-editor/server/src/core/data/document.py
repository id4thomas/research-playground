"""Document tree — Markdown 파싱 결과를 표현 (UUID 기반).

블록은 안정적인 UUID(`id`)로 식별하고, 섹션은 블록을 `blocks: dict[id→Block]` 로
보관하되 표시 순서는 `order: list[id]` 로 분리한다. 편집/삽입/삭제가 누적돼도 id는
불변이므로 히스토리 ref(액션이 가리키는 대상)가 어긋나지 않는다.

계층:
  Document
  ├─ sections: dict[code → Section]
  │            Section
  │            ├─ meta:   SectionMeta
  │            ├─ blocks: dict[block_id → Block]
  │            └─ order:  list[block_id]   (표시 순서)
  └─ outline: list[SectionMeta]  (섹션 표시 순서 + 계층 보존)

참고: 블록 식별은 UUID가 근본(wire/프론트엔드와 주고받는 값)이고, LLM 프롬프트에서는
가독성을 위해 `[code;ordinal]` 형태의 읽기 쉬운 ref로 렌더링한다. ordinal ↔ id 매핑은
`Section.order` 로 복원한다 (`order[ordinal]`).
"""
from __future__ import annotations

import uuid
from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field


def new_block_id() -> str:
    return uuid.uuid4().hex


class _BaseBlock(BaseModel):
    id: str = Field(default_factory=new_block_id)
    content: str = ""
    # 콘텐츠 표현 포맷. 허용값은 블록 타입마다 다르므로 각 서브클래스에서 Literal로 좁힌다.
    format: str = ""


class TextBlock(_BaseBlock):
    type: Literal["text"] = "text"
    format: Literal["markdown", "html"] = "markdown"


class TableBlock(_BaseBlock):
    type: Literal["table"] = "table"
    format: Literal["markdown", "html"] = "html"


class EquationBlock(_BaseBlock):
    type: Literal["equation"] = "equation"
    format: Literal["tex", "html"] = "tex"


Block = Annotated[
    Union[TextBlock, TableBlock, EquationBlock],
    Field(discriminator="type"),
]

# 블록 타입별 (기본 format, 허용 format 집합).
_DEFAULT_FORMAT = {"text": "markdown", "table": "html", "equation": "tex"}
_ALLOWED_FORMAT = {
    "text": {"markdown", "html"},
    "table": {"markdown", "html"},
    "equation": {"tex", "html"},
}


def make_block(
    block_type: str,
    content: str,
    *,
    id: str | None = None,
    format: str | None = None,
) -> Block:
    """type 문자열로 적절한 Block 구체 타입을 생성한다.

    format 을 주지 않거나 해당 타입에 허용되지 않는 값이면 타입별 기본값
    (text=markdown, table=html, equation=tex)으로 대체한다.
    """
    block_type = block_type if block_type in _DEFAULT_FORMAT else "text"
    cls = {"text": TextBlock, "equation": EquationBlock, "table": TableBlock}[block_type]
    if format not in _ALLOWED_FORMAT[block_type]:
        format = _DEFAULT_FORMAT[block_type]
    kwargs: dict = {"content": content, "format": format}
    if id:
        kwargs["id"] = id
    return cls(**kwargs)


class SectionMeta(BaseModel):
    code: str          # "S1", "S1-1", "S2-1-1", ...
    title: str
    level: int         # 1 = #, 2 = ##, ...
    children: list[str] = Field(default_factory=list)


class Section(BaseModel):
    meta: SectionMeta
    blocks: dict[str, Block] = Field(default_factory=dict)
    order: list[str] = Field(default_factory=list)

    def ordered_blocks(self) -> list[Block]:
        """표시 순서대로 블록을 반환 (order에 있는 id만)."""
        return [self.blocks[bid] for bid in self.order if bid in self.blocks]

    def block_at(self, ordinal: int) -> Block | None:
        """LLM이 쓰는 0-base ordinal → 블록."""
        if 0 <= ordinal < len(self.order):
            return self.blocks.get(self.order[ordinal])
        return None

    def id_at(self, ordinal: int) -> str | None:
        if 0 <= ordinal < len(self.order):
            return self.order[ordinal]
        return None


class Document(BaseModel):
    """Document represented as an ordered dict of section_code → Section."""
    sections: dict[str, Section] = Field(default_factory=dict)
    outline: list[SectionMeta] = Field(default_factory=list)

    def find_block(self, block_id: str) -> tuple[Section | None, Block | None]:
        """block UUID로 (소속 섹션, 블록)을 찾는다. 없으면 (None, None)."""
        for sec in self.sections.values():
            b = sec.blocks.get(block_id)
            if b is not None:
                return sec, b
        return None, None
