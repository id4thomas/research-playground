"""Document tree — Markdown 파싱 결과를 표현.

계층:
  Document
  ├─ sections: dict[code → Section]
  │            Section
  │            ├─ meta: SectionMeta
  │            └─ blocks: list[Block]
  └─ outline: list[SectionMeta]  (표시 순서 보존)
"""
from typing import Literal

from pydantic import BaseModel, Field


class Block(BaseModel):
    type: Literal["text", "equation", "table"] = "text"
    content: str


class SectionMeta(BaseModel):
    code: str          # "S1", "S1-1", "S2-1-1", ...
    title: str
    level: int         # 1 = #, 2 = ##, ...
    children: list[str] = Field(default_factory=list)


class Section(BaseModel):
    meta: SectionMeta
    blocks: list[Block] = Field(default_factory=list)


class Document(BaseModel):
    """Document represented as an ordered dict of section_code → Section."""
    sections: dict[str, Section] = Field(default_factory=dict)
    outline: list[SectionMeta] = Field(default_factory=list)
