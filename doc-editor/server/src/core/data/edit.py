"""Document edit payloads (정규 형태) — 블록 수준과 outline(섹션 트리) 수준.

문서를 바꾸는 두 종류의 "edit" 을 한 모듈에 둔다:
  - `BlockEdit`   : 한 블록의 본문을 바꾼다 (REWRITE/REPLACE/INSERT). REWRITE/INSERT 는
                    조립된 `Block` 을 그대로 들고 있어 wire 가 변환 없이 재사용한다.
  - `OutlineEdit` : 섹션 트리를 바꾼다 (RENAME/ADD/REMOVE/MERGE). 본문이 아니라 구조.

둘 다 "무엇을 어떻게 바꾸는가"(`action` op + 페이로드)만 담는 도메인 모델이다.
대상 식별(ref)·상태·사람이 읽을 설명 같은 상호작용 메타는 여기 두지 않고 wire 쪽
(`core.data.chat` 의 `BlockInteraction`/`OutlineInteraction`)이 감싼다. LLM이 직접 뱉는
평탄(flat)한 블록 입력 모델은 operations 레이어(`edit_generate.LLMEdit`)에 분리해 둔다.
"""
from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field

from .document import Block


class RewriteBlockEdit(BaseModel):
    action: Literal["REWRITE"] = "REWRITE"
    block: Block            # 같은 블록을 재작성 → 원본 id/타입/format 을 유지한 조립 블록.
    summary: str = ""


class ReplaceBlockEdit(BaseModel):
    action: Literal["REPLACE"] = "REPLACE"
    source: str
    target: str
    summary: str = ""


class InsertBlockEdit(BaseModel):
    action: Literal["INSERT"] = "INSERT"
    block: Block            # 앵커 블록 아래에 새로 삽입할 블록.
    summary: str = ""


BlockEdit = Annotated[
    Union[RewriteBlockEdit, ReplaceBlockEdit, InsertBlockEdit],
    Field(discriminator="action"),
]


# --- Outline edit (섹션 트리 변경 — 본문 변경 없음). v1: RENAME / ADD / REMOVE / MERGE ---
class RenameOutlineEdit(BaseModel):
    action: Literal["RENAME"] = "RENAME"
    target: str             # 대상 섹션 코드.
    title: str = ""         # 새 제목.


class AddOutlineEdit(BaseModel):
    action: Literal["ADD"] = "ADD"
    target: str | None = None   # 부모 섹션 코드 (None = 루트 레벨).
    title: str = ""             # 새 제목.
    level: int | None = None    # 헤더 레벨 (None이면 parent.level+1, 루트는 1).
    position: int | None = None  # 부모 children 중 0-based 삽입 위치 (None = 맨 뒤).


class RemoveOutlineEdit(BaseModel):
    action: Literal["REMOVE"] = "REMOVE"
    target: str             # 대상 섹션 코드. 섹션과 그 안의 모든 블록·하위 섹션이 함께 삭제된다.


class MergeOutlineEdit(BaseModel):
    action: Literal["MERGE"] = "MERGE"
    # 합칠 섹션 코드 목록. outline 표시 순서상 연속이어야 하며, 첫 번째 코드가 생존
    # 섹션이 된다. 나머지의 모든 블록(하위 섹션 블록 포함)이 생존 섹션 뒤에 순서대로
    # 이어붙고 나머지 섹션은 제거된다.
    targets: list[str] = Field(default_factory=list)
    title: str | None = None    # 생존 섹션의 새 제목 (None이면 첫 target 제목 유지).
    level: int | None = None    # 생존 섹션의 새 레벨 (None이면 첫 target 레벨 유지).


OutlineEdit = Annotated[
    Union[RenameOutlineEdit, AddOutlineEdit, RemoveOutlineEdit, MergeOutlineEdit],
    Field(discriminator="action"),
]
