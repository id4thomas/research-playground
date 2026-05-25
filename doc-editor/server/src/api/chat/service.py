from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from agent.base import BaseAgent
from agent.doc_answerer.graph import DocAnswererAgent
from agent.doc_assistant.graph import DocAssistantAgent
from agent.doc_clarifier.graph import DocClarifierAgent
from agent.doc_editor.graph import DocEditorAgent
from agent.doc_restructurer.graph import DocRestructurerAgent
from agent.modules.strip_codes import strip_section_codes
from api.chat.dto import ChatMessage, ChatRequest, ChatResponse
from core.exceptions import GraphExecutionError
from core.langchain.usage import TokenUsage
from core.logger import get_logger
from core.tracing import start_span

logger = get_logger(__name__)

_assistant = DocAssistantAgent()
_editor = DocEditorAgent()
_restructurer = DocRestructurerAgent()
_answerer = DocAnswererAgent()
_clarifier = DocClarifierAgent()


# ---------------------------------------------------------------------------
# Usage aggregation
# ---------------------------------------------------------------------------
_USAGE_STATE_KEYS = ("intent_router", "context", "edit", "restructure", "answer", "clarify")


def aggregate_usage(state: dict) -> TokenUsage:
    """Sum token_usage across all per-module outputs present in the agent state."""
    total = TokenUsage()
    for key in _USAGE_STATE_KEYS:
        out = state.get(key)
        usage = getattr(out, "token_usage", None) if out is not None else None
        if usage is not None:
            total = total.add(usage)
    return total


# ---------------------------------------------------------------------------
# History serialization — ChatMessage(rich) → LangChain BaseMessage(텍스트)
# ---------------------------------------------------------------------------
_INTENT_LABEL = {
    "edit": "편집 제안",
    "clarify": "사용자에게 질문",
    "answer": "답변",
    "restructure": "섹션 구조 변경 제안",
}

_STATUS_LABEL = {
    "accepted": "수락",
    "declined": "거절",
    "instructed": "직접 지시",
    "pending": "대기",
}

_CIRCLED = ["①", "②", "③", "④", "⑤", "⑥", "⑦", "⑧", "⑨", "⑩"]


def _circled(i: int) -> str:
    return _CIRCLED[i] if i < len(_CIRCLED) else f"({i + 1})"


def _format_assistant_content(m: ChatMessage) -> str:
    intent_label = _INTENT_LABEL.get(m.intent or "", None)
    header = f"[ASSISTANT · {intent_label}]" if intent_label else "[ASSISTANT]"
    body = m.content or ""
    out = f"{header} {body}".rstrip()

    if m.clarify_options:
        opts = "\n".join(f"  {_circled(i)} {opt}" for i, opt in enumerate(m.clarify_options))
        out += f"\n\n[제시된 선택지]\n{opts}"

    if m.edit_proposals:
        blocks = []
        for i, p in enumerate(m.edit_proposals):
            status_part = _STATUS_LABEL.get(p.status, p.status)
            if p.status == "instructed" and p.instruction:
                status_part = f'직접 지시("{p.instruction}")'
            lines = [f"  #{i + 1} [{p.action}] {p.target_desc or p.ref} → {status_part}"]
            if p.summary:
                lines.append(f"      · 의도: {p.summary}")
            if p.content:
                lines.append(f"      · 내용: {p.content}")
            blocks.append("\n".join(lines))
        out += "\n\n[제시된 블록 수정 제안]\n" + "\n\n".join(blocks)

    if m.outline_proposals:
        blocks = []
        for i, p in enumerate(m.outline_proposals):
            status_part = _STATUS_LABEL.get(p.status, p.status)
            if p.status == "instructed" and p.instruction:
                status_part = f'직접 지시("{p.instruction}")'
            lines = [f"  #{i + 1} [{p.action}] {p.target_desc} → {status_part}"]
            if p.summary:
                lines.append(f"      · 의도: {p.summary}")
            blocks.append("\n".join(lines))
        out += "\n\n[제시된 섹션 구조 변경]\n" + "\n\n".join(blocks)

    return out


def _format_user_content(m: ChatMessage, prev: ChatMessage | None) -> str:
    if (
        m.picked_option_index is not None
        and prev is not None
        and prev.role == "assistant"
        and prev.clarify_options
        and 0 <= m.picked_option_index < len(prev.clarify_options)
    ):
        return f"[USER · 선택지 {_circled(m.picked_option_index)} 채택] {m.content}"
    return f"[USER] {m.content}"


def to_lc_messages(messages: list[ChatMessage]) -> list[BaseMessage]:
    out: list[BaseMessage] = []
    prev: ChatMessage | None = None
    for m in messages:
        if m.role == "user":
            out.append(HumanMessage(content=_format_user_content(m, prev)))
        elif m.role == "assistant":
            out.append(AIMessage(content=_format_assistant_content(m)))
        else:
            out.append(AIMessage(content=m.content))
        prev = m
    return out


def initial_state(req: ChatRequest) -> dict:
    return {
        "messages": to_lc_messages(req.messages),
        "document": req.document,
        "selected": req.selected,
    }


# ---------------------------------------------------------------------------
# Orchestrated chat
# ---------------------------------------------------------------------------
async def run_chat(req: ChatRequest) -> ChatResponse:
    try:
        with start_span("chat_request") as span:
            span.set_inputs({"project_id": req.project_id, "selected": req.selected})
            result = await _assistant.invoke(initial_state(req))
            orch = result.get("intent_router")
            final = result.get("final")
            resp_intent = orch.intent if orch else ""
            span.set_outputs(
                {
                    "intent": resp_intent,
                    "final_message": final.message if final else "",
                }
            )
    except Exception as e:
        logger.exception("doc_assistant graph execution failed")
        raise GraphExecutionError(str(e), graph="doc_assistant") from e

    reason = orch.suggest_new_session_reason if orch else None
    if reason:
        reason = strip_section_codes(reason, req.document)

    return ChatResponse(
        message=ChatMessage(role="assistant", content=final.message if final else ""),
        edits=final.edits if final else {},
        outline_actions=final.outline_actions if final else [],
        intent=resp_intent,
        suggest_new_session=bool(orch.suggest_new_session) if orch else False,
        suggest_new_session_reason=reason,
        clarify_options=final.clarify_options if final else [],
        token_usage=aggregate_usage(result),
    )


# ---------------------------------------------------------------------------
# Direct subgraph runs (/api/chat/{intent})
# ---------------------------------------------------------------------------
async def _run_subgraph(agent: BaseAgent, req: ChatRequest, intent: str) -> ChatResponse:
    try:
        result = await agent.invoke(initial_state(req))
    except Exception as e:
        logger.exception("%s subgraph execution failed", intent)
        raise GraphExecutionError(str(e), graph=intent) from e
    final = result.get("final")
    return ChatResponse(
        message=ChatMessage(role="assistant", content=final.message if final else ""),
        edits=final.edits if final else {},
        outline_actions=final.outline_actions if final else [],
        clarify_options=final.clarify_options if final else [],
        intent=intent,
        token_usage=aggregate_usage(result),
    )


async def run_edit(req: ChatRequest) -> ChatResponse:
    return await _run_subgraph(_editor, req, "edit")


async def run_restructure(req: ChatRequest) -> ChatResponse:
    return await _run_subgraph(_restructurer, req, "restructure")


async def run_answer(req: ChatRequest) -> ChatResponse:
    return await _run_subgraph(_answerer, req, "answer")


async def run_clarify(req: ChatRequest) -> ChatResponse:
    return await _run_subgraph(_clarifier, req, "clarify")
