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
from core.logger import get_logger
from core.tracing import start_span

logger = get_logger(__name__)

_assistant = DocAssistantAgent()
_editor = DocEditorAgent()
_restructurer = DocRestructurerAgent()
_answerer = DocAnswererAgent()
_clarifier = DocClarifierAgent()


def to_lc_messages(messages: list[ChatMessage]) -> list[BaseMessage]:
    out: list[BaseMessage] = []
    for m in messages:
        cls = HumanMessage if m.role == "user" else AIMessage
        out.append(cls(content=m.content))
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
    )


async def run_edit(req: ChatRequest) -> ChatResponse:
    return await _run_subgraph(_editor, req, "edit")


async def run_restructure(req: ChatRequest) -> ChatResponse:
    return await _run_subgraph(_restructurer, req, "restructure")


async def run_answer(req: ChatRequest) -> ChatResponse:
    return await _run_subgraph(_answerer, req, "answer")


async def run_clarify(req: ChatRequest) -> ChatResponse:
    return await _run_subgraph(_clarifier, req, "clarify")
