"""Wire 스펙 ↔ LLM 스펙 변환.

두 메시지 표현은 의도적으로 분리돼 있다:
  - wire (`core.data.chat.ChatMessage`)  : 프론트엔드와 주고받음. UUID ref + 구조화 액션.
  - LLM  (`agent.base.LLMChatMessage`)   : 모델에 넣는 role/content 텍스트.

이 모듈은 둘 사이를 잇는다:
  - `wire_to_llm`      : wire 히스토리 → LLM 텍스트 턴. 블록 UUID를 `[uuid]`로
                         노출해(문서 렌더와 동일 키) 액션↔현재 블록을 연결 가능케 하고,
                         target_desc/요약/상태는 사람이 읽기 위한 보조로 함께 렌더.
  - `assemble_message` : 에이전트 결과(읽기 쉬운 ref) → wire 응답 메시지 (ref→UUID 매핑).
"""
from __future__ import annotations

from core.data import (
    Document,
    InsertEdit,
    ReplaceEdit,
    RewriteEdit,
    make_block,
)
from core.data.chat import (
    AddOutlineAction,
    BaseChatMessage,
    ChatMessage,
    ClarifyChatMessage,
    InsertBlockAction,
    InteractionAction,
    InteractionChatMessage,
    MergeOutlineAction,
    RemoveOutlineAction,
    RenameOutlineAction,
    ReplaceBlockAction,
    RewriteBlockAction,
)

_STATUS_LABEL = {
    "accepted": "수락",
    "declined": "거절",
    "instructed": "직접 지시",
    "pending": "대기",
}
def _assistant_label(m: BaseChatMessage) -> str:
    """메시지 type(+action scope)에서 어시스턴트 행위 라벨을 파생한다 (별도 intent 없음)."""
    if isinstance(m, ClarifyChatMessage):
        return "사용자에게 질문"
    if isinstance(m, InteractionChatMessage):
        if any(getattr(a, "scope", None) == "outline" for a in m.actions):
            return "섹션 구조 변경 제안"
        return "편집 제안"
    return "답변"


# ---------------------------------------------------------------------------
# wire → LLM (히스토리 직렬화)
# ---------------------------------------------------------------------------
def _action_content(a: InteractionAction) -> str:
    if isinstance(a, (RewriteBlockAction, InsertBlockAction)):
        return a.block.content
    if isinstance(a, ReplaceBlockAction):
        return f'"{a.source}" → "{a.target}"'
    if isinstance(a, (RenameOutlineAction, AddOutlineAction)):
        return a.title
    return ""


def _render_actions(actions: list[InteractionAction]) -> str:
    lines: list[str] = []
    for i, a in enumerate(actions):
        status = _STATUS_LABEL.get(a.status, a.status)
        if a.status == "instructed" and a.instruction:
            status = f'직접 지시("{a.instruction}")'
        # 블록 UUID를 그대로 노출한다. 문서 렌더(render_document)가 같은 `[uuid]`
        # 키로 블록을 출력하므로, 모델이 히스토리 액션 ↔ 현재 블록을 결정적으로
        # 연결할 수 있다. target_desc('…섹션 내 블록')는 사람이 읽기 위한 섹션 보조.
        ref = getattr(a, "ref", "") or ""
        parts = []
        if ref:
            parts.append(f"[{ref}]")
        if a.target_desc:
            parts.append(a.target_desc)
        desc = " ".join(parts) or ref
        lines.append(f"  #{i + 1} [{a.action}] {desc} → {status}")
        if a.summary:
            lines.append(f"      · 의도: {a.summary}")
        content = _action_content(a)
        if content:
            lines.append(f"      · 내용: {content}")
    return "\n".join(lines)


def _format_assistant(m: BaseChatMessage) -> str:
    # clarify 의 선택지 목록(clarify_options)은 히스토리에 싣지 않는다 —
    # 질문 본문만 남기고, 사용자가 고른 값은 다음 user 턴 content 로 들어온다.
    header = f"[ASSISTANT · {_assistant_label(m)}]"
    out = f"{header} {m.content or ''}".rstrip()
    if isinstance(m, InteractionChatMessage) and m.actions:
        out += "\n\n[제시된 문서 액션]\n" + _render_actions(m.actions)
    return out


def _format_user(m: BaseChatMessage) -> str:
    # 선택지를 고른 경우(OptionReply)도 고른 값(content)만 그대로 싣는다.
    out = f"[USER] {m.content or ''}".rstrip()
    if isinstance(m, InteractionChatMessage) and m.actions:
        out += "\n\n[사용자 조치]\n" + _render_actions(m.actions)
    return out


def wire_to_llm(messages: list[ChatMessage]) -> list[dict]:
    """wire ChatMessage 리스트 → LLM 텍스트 턴 ({'role','content'} dict)."""
    out: list[dict] = []
    for m in messages:
        if m.role == "user":
            out.append({"role": "user", "content": _format_user(m)})
        elif m.role == "assistant":
            out.append({"role": "assistant", "content": _format_assistant(m)})
        else:
            out.append({"role": m.role, "content": m.content})
    return out


# ---------------------------------------------------------------------------
# 에이전트 결과 → wire 응답 메시지 (읽기 쉬운 ref → UUID)
# ---------------------------------------------------------------------------
def _resolve(document: Document, ref: str):
    """블록 UUID ref → (section, block, target_desc).

    target_desc는 사람이 읽기 위한 섹션 맥락만 담는다. 블록 식별은 `[uuid]`가
    전담하므로 'N번째 블록' 같은 상대 위치 표현은 쓰지 않는다(편집이 누적되면
    순서가 어긋나 오히려 오해를 부른다)."""
    sec, block = document.find_block(ref)
    if sec is None:
        return None, None, ""
    return sec, block, f"'{sec.meta.title}' 섹션 내 블록"


def _edits_to_actions(document: Document, edits_map: dict) -> list[InteractionAction]:
    actions: list[InteractionAction] = []
    for ref, edits in edits_map.items():
        _sec, orig, desc = _resolve(document, ref)
        for e in edits:
            if isinstance(e, RewriteEdit):
                # 같은 블록을 재작성 → 원본 id/타입/format 을 유지.
                block = make_block(
                    orig.type if orig else "text", e.value, id=ref,
                    format=orig.format if orig else None,
                )
                actions.append(RewriteBlockAction(
                    ref=ref, block=block, summary=e.summary, target_desc=desc))
            elif isinstance(e, ReplaceEdit):
                actions.append(ReplaceBlockAction(
                    ref=ref, source=e.source, target=e.target,
                    summary=e.summary, target_desc=desc))
            elif isinstance(e, InsertEdit):
                actions.append(InsertBlockAction(
                    ref=ref, block=e.value, summary=e.summary, target_desc=desc))
    return actions


def _outline_to_actions(document: Document, outline_actions: list) -> list[InteractionAction]:
    out: list[InteractionAction] = []
    for oa in outline_actions:
        ref = oa.target
        desc = ""
        if ref and ref in document.sections:
            desc = f"'{document.sections[ref].meta.title}' 섹션"
        if oa.action == "ADD":
            out.append(AddOutlineAction(
                ref=oa.target, title=oa.title or "", level=oa.level,
                position=oa.position, target_desc=desc))
        elif oa.action == "MERGE":
            targets = oa.targets or []
            out.append(MergeOutlineAction(
                ref=targets[0] if targets else None, targets=targets,
                title=oa.title, level=oa.level, target_desc=desc))
        elif oa.action == "RENAME":
            out.append(RenameOutlineAction(ref=oa.target, title=oa.title or "", target_desc=desc))
        elif oa.action == "REMOVE":
            out.append(RemoveOutlineAction(ref=oa.target, target_desc=desc))
    return out


def assemble_message(
    *,
    content: str,
    document: Document,
    edits_map: dict | None = None,
    outline_actions: list | None = None,
    clarify_options: list[str] | None = None,
) -> ChatMessage:
    """에이전트 FinalOutput → wire 응답 메시지 (assistant).

    페이로드에 따라 메시지 타입을 고른다 (type 이 곧 행위 구분, 별도 intent 없음):
      - 문서 액션 있음 → InteractionChatMessage (edit/restructure)
      - 선택지 있음     → ClarifyChatMessage
      - 그 외           → BaseChatMessage (answer)
    """
    actions = _edits_to_actions(document, edits_map or {})
    actions += _outline_to_actions(document, outline_actions or [])
    if actions:
        return InteractionChatMessage(role="assistant", content=content, actions=actions)
    if clarify_options:
        return ClarifyChatMessage(role="assistant", content=content, clarify_options=clarify_options)
    return BaseChatMessage(role="assistant", content=content)
