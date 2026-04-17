import json
import logging

import mlflow
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from config import get_settings
from agent.research.main_graph import ResearchAgent
from agent.research.states import SearchConfig
from core.logger import get_logger

settings = get_settings()
logger = get_logger(__name__)

# Init mlflow tracing
mlflow.set_tracking_uri(settings.tracing.uri)
mlflow.set_experiment(settings.tracing.experiment)
mlflow.langchain.autolog()

# MLflow LangChain autologging uses ContextVar tokens across async contexts
# (e.g. LangGraph fan-out), which raises a spurious warning — suppress it.
logging.getLogger("mlflow.utils.autologging_utils").setLevel(logging.ERROR)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
agent = ResearchAgent()

# Nodes tracked for SSE events
_MAIN_NODES = {"generate_topics", "search_subgraph", "collect_and_rank"}
_SUB_NODES = {"generate_query", "search", "judge", "generate_feedback", "emit"}
_TRACKED_NODES = _MAIN_NODES | _SUB_NODES


def _get(obj, *keys):
    """Get a nested field from a dict or Pydantic model."""
    for key in keys:
        if obj is None:
            return None
        if isinstance(obj, dict):
            obj = obj.get(key)
        elif hasattr(obj, key):
            obj = getattr(obj, key)
        else:
            return None
    return obj


def _serialize_papers(papers) -> list[dict]:
    result = []
    for p in (papers or []):
        if isinstance(p, dict):
            result.append(p)
        elif hasattr(p, "model_dump"):
            result.append(p.model_dump())
    return result


class SearchRequest(BaseModel):
    query: str
    num_topics: int = 3
    max_attempts: int = 2
    search_limit: int = 5
    top_k: int = 10
    top_k_per_topic: int = 5
    min_required: int = 3


@app.post("/search")
async def search(request: SearchRequest):
    state = {
        "query": request.query,
        "num_topics": request.num_topics,
        "top_k": request.top_k,
        "top_k_per_topic": request.top_k_per_topic,
    }
    config = SearchConfig(
        max_attempts=request.max_attempts,
        search_limit=request.search_limit,
        min_required=request.min_required,
    )
    result = await agent.invoke(state, config=config)
    return {
        "query": result["query"],
        "topics": result["topics"],
        "papers": [p.model_dump() for p in result["result"]],
    }


@app.post("/search/stream")
async def search_stream(request: SearchRequest):
    """SSE endpoint streaming node-level events from the LangGraph execution.

    Event types
    -----------
    node_start  – a graph node began executing
    node_end    – a graph node finished; payload includes relevant output fields
    done        – graph completed; payload contains final topics + ranked papers
    error       – unhandled exception during streaming
    """

    async def event_generator():
        captured_topics: list[str] = []
        captured_papers: list[dict] = []

        try:
            state = {
                "query": request.query,
                "num_topics": request.num_topics,
                "top_k": request.top_k,
                "top_k_per_topic": request.top_k_per_topic,
            }
            config = SearchConfig(
                max_attempts=request.max_attempts,
                search_limit=request.search_limit,
                min_required=request.min_required,
            )
            async for event in agent.astream(state, config=config):
                kind = event["event"]
                node = event["metadata"].get("langgraph_node", "")
                name = event["name"]

                # Keep only top-level node chain events (not inner LLM/tool events)
                if name not in _TRACKED_NODES or name != node:
                    continue

                inp = event["data"].get("input")
                out = event["data"].get("output")

                # Topic is on the subgraph input state; not present in main-graph nodes
                topic = _get(inp, "topic")
                payload: dict = {"node": node}
                if topic:
                    payload["topic"] = topic

                if kind == "on_chain_start":
                    if node == "generate_query":
                        attempt = _get(inp, "attempt")
                        if attempt is not None:
                            payload["attempt"] = attempt

                    yield f"event: node_start\ndata: {json.dumps(payload)}\n\n"

                elif kind == "on_chain_end":
                    if node == "generate_topics":
                        topics = _get(out, "topics") or []
                        captured_topics = list(topics)
                        payload["topics"] = captured_topics

                    elif node == "generate_query":
                        payload["search_query"] = _get(out, "search_query") or ""

                    elif node == "search":
                        papers = _get(out, "papers") or []
                        payload["papers_found"] = len(papers)

                    elif node == "judge":
                        papers = _get(out, "papers") or []
                        payload["papers_relevant"] = len(papers)

                    elif node == "generate_feedback":
                        payload["feedback"] = _get(out, "feedback") or ""

                    elif node == "search_subgraph":
                        subgraph_results = _get(out, "subgraph_results") or []
                        total = sum(len(_get(r, "papers") or []) for r in subgraph_results)
                        payload["papers_emitted"] = total

                    elif node == "collect_and_rank":
                        papers = _get(out, "result") or []
                        captured_papers = _serialize_papers(papers)
                        payload["papers_count"] = len(captured_papers)

                    yield f"event: node_end\ndata: {json.dumps(payload)}\n\n"

            done_payload = {
                "query": request.query,
                "topics": captured_topics,
                "papers": captured_papers,
            }
            yield f"event: done\ndata: {json.dumps(done_payload)}\n\n"

        except Exception as e:
            logger.exception("SSE stream error")
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
