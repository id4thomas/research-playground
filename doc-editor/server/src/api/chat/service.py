from agent.graphs.doc_answerer.graph import AnswererState, DocAnswererAgent
from agent.graphs.doc_assistant.graph import DocAssistantAgent
from agent.graphs.doc_assistant.states import AgentState
from agent.graphs.doc_clarifier.graph import ClarifierState, DocClarifierAgent
from agent.graphs.doc_editor.graph import DocEditorAgent, EditorState
from agent.graphs.doc_restructurer.graph import DocRestructurerAgent, RestructurerState
from agent.operations import StripCodesOperation
from api.chat.dto import ChatRequest, ChatResponse
from api.chat.serialize import assemble_message, wire_to_llm
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
# History serialization — wire ChatMessage → LLM 텍스트 턴 (api.chat.serialize)
# ---------------------------------------------------------------------------
to_messages = wire_to_llm


# ---------------------------------------------------------------------------
# Orchestrated chat
# ---------------------------------------------------------------------------
async def run_chat(req: ChatRequest) -> ChatResponse:
    try:
        with start_span("chat_request") as span:
            span.set_inputs({"project_id": req.project_id, "selected": req.selected})
            state = AgentState(
                messages=to_messages(req.messages),
                document=req.document,
                selected=req.selected,
            )
            result = await _assistant.invoke(state)
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
        reason = await StripCodesOperation.run(reason, req.document)

    return ChatResponse(
        message=assemble_message(
            content=final.message if final else "",
            document=req.document,
            intent=resp_intent,
            edits_map=final.edits if final else {},
            outline_actions=final.outline_actions if final else [],
            clarify_options=final.clarify_options if final else [],
        ),
        intent=resp_intent,
        suggest_new_session=bool(orch.suggest_new_session) if orch else False,
        suggest_new_session_reason=reason,
        token_usage=aggregate_usage(result),
    )


# ---------------------------------------------------------------------------
# Direct subgraph runs (/api/chat/{intent})
# ---------------------------------------------------------------------------
def _subgraph_response(result: dict, intent: str, document) -> ChatResponse:
    final = result.get("final")
    return ChatResponse(
        message=assemble_message(
            content=final.message if final else "",
            document=document,
            intent=intent,
            edits_map=final.edits if final else {},
            outline_actions=final.outline_actions if final else [],
            clarify_options=final.clarify_options if final else [],
        ),
        intent=intent,
        token_usage=aggregate_usage(result),
    )


async def run_edit(req: ChatRequest) -> ChatResponse:
    state = EditorState(
        messages=to_messages(req.messages),
        document=req.document,
        selected=req.selected,
    )
    try:
        result = await _editor.invoke(state)
    except Exception as e:
        logger.exception("edit subgraph execution failed")
        raise GraphExecutionError(str(e), graph="edit") from e
    return _subgraph_response(result, "edit", req.document)


async def run_restructure(req: ChatRequest) -> ChatResponse:
    state = RestructurerState(
        messages=to_messages(req.messages),
        document=req.document,
        selected=req.selected,
    )
    try:
        result = await _restructurer.invoke(state)
    except Exception as e:
        logger.exception("restructure subgraph execution failed")
        raise GraphExecutionError(str(e), graph="restructure") from e
    return _subgraph_response(result, "restructure", req.document)


async def run_answer(req: ChatRequest) -> ChatResponse:
    state = AnswererState(
        messages=to_messages(req.messages),
        document=req.document,
        selected=req.selected,
    )
    try:
        result = await _answerer.invoke(state)
    except Exception as e:
        logger.exception("answer subgraph execution failed")
        raise GraphExecutionError(str(e), graph="answer") from e
    return _subgraph_response(result, "answer", req.document)


async def run_clarify(req: ChatRequest) -> ChatResponse:
    state = ClarifierState(
        messages=to_messages(req.messages),
        document=req.document,
        selected=req.selected,
    )
    try:
        result = await _clarifier.invoke(state)
    except Exception as e:
        logger.exception("clarify subgraph execution failed")
        raise GraphExecutionError(str(e), graph="clarify") from e
    return _subgraph_response(result, "clarify", req.document)
