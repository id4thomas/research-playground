"""Section-tree mutations (outline level — 본문 변경 없음)."""
from typing import Literal

from pydantic import BaseModel


class OutlineAction(BaseModel):
    """Section-tree mutation. v1: RENAME / ADD / REMOVE / MERGE."""
    action: Literal["RENAME", "ADD", "REMOVE", "MERGE"]
    # RENAME/REMOVE: 대상 섹션 코드.
    # ADD: 부모 섹션 코드 (None = 루트 레벨).
    # MERGE: 사용 안함 (targets 사용).
    target: str | None = None
    # MERGE: 합칠 섹션 코드 목록. outline 표시 순서상 연속이어야 하며,
    # 첫 번째 코드가 생존 섹션이 된다. 나머지의 모든 블록(하위 섹션 블록 포함)이
    # 생존 섹션 뒤에 순서대로 이어붙고 나머지 섹션은 제거된다.
    targets: list[str] | None = None
    # ADD/RENAME/MERGE: 새 제목 (MERGE는 None이면 첫 target 제목 유지).
    title: str | None = None
    # ADD: 헤더 레벨 (None이면 parent.level+1, 루트는 1).
    # MERGE: 생존 섹션의 새 레벨 (None이면 첫 target 레벨 유지).
    level: int | None = None
    # ADD: 부모 children 중 0-based 삽입 위치 (None = 맨 뒤).
    position: int | None = None
