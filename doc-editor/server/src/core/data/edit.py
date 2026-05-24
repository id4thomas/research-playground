"""Block-level edit actions.

LLM이 반환하는 평탄한 `LLMEdit`을 서버에서 검증/분기한 뒤
`RewriteEdit | ReplaceEdit | InsertEdit` 하나로 좁힌다 (=== `Edit`).
"""
from typing import Literal, Union

from pydantic import BaseModel, Field

from .document import Block


class LLMEdit(BaseModel):
    """LLM이 직접 뱉는 평탄한 edit 모델 (서버에서 Edit으로 좁힌다)."""
    ref: str = Field(description='블록 식별자. 예: "S1;0", "S1-2;3".')
    action: Literal["REWRITE", "REPLACE", "INSERT"]
    value: str | None = None
    value_type: Literal["text", "equation", "table"] | None = None
    source: str | None = None
    target: str | None = None


class RewriteEdit(BaseModel):
    action: Literal["REWRITE"] = "REWRITE"
    value: str


class ReplaceEdit(BaseModel):
    action: Literal["REPLACE"] = "REPLACE"
    source: str
    target: str


class InsertEdit(BaseModel):
    action: Literal["INSERT"] = "INSERT"
    value: Block


Edit = Union[RewriteEdit, ReplaceEdit, InsertEdit]
