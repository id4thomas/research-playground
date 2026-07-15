import json

from ddtrace.llmobs import LLMObs
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from agent.data.search_option import SearchOption
from agent.graphs.hf_paper_search.graph import graph
from agent.graphs.deep_research.graph import graph as deep_research_graph
from agent.graphs.deep_research_alt.graph import graph as deep_research_alt_graph

from api.dto import (
    DeepResearchRequest,
    DeepResearchResponse,
    PaperResult,
    SearchRequest,
    SearchResponse,
    TopicPapersResult,
)

router = APIRouter()


@router.post("/search", response_model=SearchResponse)
async def search(request: Request, body: SearchRequest) -> SearchResponse:
    option = SearchOption(
        search_limit=body.search_limit,
        min_required=body.min_required,
        max_iteration=body.max_iteration,
        score_threshold=body.score_threshold,
    )

    with LLMObs.workflow(name="search") as span:
        # LLMObs.annotate(span=span, tags={"feature": "search"})

        result = await graph.ainvoke(
            {"topic": body.topic, "option": option},
            config={
                "configurable": {
                    "hf_client": request.app.state.hf_client,
                    "openai_client": request.app.state.openai_client,
                }
            },
        )
        # LLMObs.annotate(
        #     span=span,
        #     input_data=body.topic,
        #     output_data= None,
        # )
        return result
    

    papers = [
        PaperResult(
            id=r.data.id,
            title=r.data.title,
            summary=r.data.summary,
            authors=r.data.authors,
            score=r.score,
            source_query=r.source_query,
        )
        for r in result.get("final", [])
    ]
    return SearchResponse(
        topic=body.topic,
        iteration=result.get("iteration", 0),
        papers=papers,
    )


@router.post("/deep-research", response_model=DeepResearchResponse)
async def deep_research(request: Request, body: DeepResearchRequest) -> DeepResearchResponse:
    option = SearchOption(
        search_limit=body.search_limit,
        min_required=body.min_required,
        max_iteration=body.max_iteration,
        score_threshold=body.score_threshold,
    )

    with LLMObs.workflow(name="deep_research"):
        result = await deep_research_graph.ainvoke(
            {
                "instruction": body.instruction,
                "n_topics": body.n_topics,
                "max_research_iteration": body.max_research_iteration,
                "option": option,
            },
            config={
                "configurable": {
                    "hf_client": request.app.state.hf_client,
                    "openai_client": request.app.state.openai_client,
                }
            },
        )

    results = [
        TopicPapersResult(
            topic=r.topic,
            papers=[
                PaperResult(
                    id=p.data.id,
                    title=p.data.title,
                    summary=p.data.summary,
                    authors=p.data.authors,
                    score=p.score,
                    source_query=p.source_query,
                )
                for p in r.result
            ],
        )
        for r in result.get("results", [])
    ]
    return DeepResearchResponse(
        instruction=body.instruction,
        topics=result.get("topics", []),
        review=result.get("review", ""),
        results=results,
        report=result.get("report", ""),
    )


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def _serialize_node_update(node: str, patch: dict) -> dict:
    """노드별 state patch에서 클라이언트에 보여줄 정보만 추출"""
    if node == "topic_generation":
        return {"topics": patch.get("pending_topics", [])}
    if node == "search":
        return {
            "topics": patch.get("topics", []),
            "n_papers": len(patch.get("retrieved", [])),
            "iteration": patch.get("research_iteration", 0),
        }
    if node == "review":
        return {
            "review": patch.get("review", ""),
            "followup_topics": patch.get("pending_topics", []),
        }
    if node == "aggregation":
        return {"results": [r.model_dump() for r in patch.get("results", [])]}
    if node == "report":
        return {"report": patch.get("report", "")}
    # deep_research_alt: create_agent 수퍼바이저 완료 (마지막 메시지 = 검토 의견)
    if node == "supervisor":
        messages = patch.get("messages") or []
        return {
            "review": messages[-1].content if messages else "",
            "topics": patch.get("topics", []),
            "n_papers": len(patch.get("retrieved", [])),
        }
    return {}


def _stream_graph(target_graph, inputs: dict, config: dict, workflow_name: str) -> StreamingResponse:
    """그래프 실행을 SSE로 중계"""

    async def event_generator():
        try:
            with LLMObs.workflow(name=workflow_name):
                async for mode, chunk in target_graph.astream(
                    inputs, config, stream_mode=["updates", "custom"]
                ):
                    if mode == "custom":
                        # 노드가 emit하는 토픽별 진행 이벤트
                        yield _sse(chunk)
                        continue
                    for node, patch in chunk.items():
                        yield _sse({
                            "type": "node_update",
                            "node": node,
                            "data": _serialize_node_update(node, patch or {}),
                        })
            yield _sse({"type": "done"})
        except Exception as e:
            yield _sse({"type": "error", "message": str(e)})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/deep-research/stream")
async def deep_research_stream(request: Request, body: DeepResearchRequest) -> StreamingResponse:
    option = SearchOption(
        search_limit=body.search_limit,
        min_required=body.min_required,
        max_iteration=body.max_iteration,
        score_threshold=body.score_threshold,
    )
    inputs = {
        "instruction": body.instruction,
        "n_topics": body.n_topics,
        "max_research_iteration": body.max_research_iteration,
        "option": option,
    }
    config = {
        "configurable": {
            "hf_client": request.app.state.hf_client,
            "openai_client": request.app.state.openai_client,
        }
    }

    return _stream_graph(deep_research_graph, inputs, config, "deep_research_stream")


@router.post("/deep-research-alt", response_model=DeepResearchResponse)
async def deep_research_alt(request: Request, body: DeepResearchRequest) -> DeepResearchResponse:
    option = SearchOption(
        search_limit=body.search_limit,
        min_required=body.min_required,
        max_iteration=body.max_iteration,
        score_threshold=body.score_threshold,
    )

    with LLMObs.workflow(name="deep_research_alt"):
        result = await deep_research_alt_graph.ainvoke(
            {
                "instruction": body.instruction,
                "n_topics": body.n_topics,
                "max_research_iteration": body.max_research_iteration,
                "option": option,
            },
            config={
                "configurable": {
                    "hf_client": request.app.state.hf_client,
                    "openai_client": request.app.state.openai_client,
                }
            },
        )

    results = [
        TopicPapersResult(
            topic=r.topic,
            papers=[
                PaperResult(
                    id=p.data.id,
                    title=p.data.title,
                    summary=p.data.summary,
                    authors=p.data.authors,
                    score=p.score,
                    source_query=p.source_query,
                )
                for p in r.result
            ],
        )
        for r in result.get("results", [])
    ]
    # supervisor의 마지막 답변(도구 호출 없는 종료 메시지)을 검토 의견으로 사용
    messages = result.get("messages", [])
    review = messages[-1].content if messages else ""
    return DeepResearchResponse(
        instruction=body.instruction,
        topics=result.get("topics", []),
        review=review,
        results=results,
        report=result.get("report", ""),
    )


@router.post("/deep-research-alt/stream")
async def deep_research_alt_stream(request: Request, body: DeepResearchRequest) -> StreamingResponse:
    option = SearchOption(
        search_limit=body.search_limit,
        min_required=body.min_required,
        max_iteration=body.max_iteration,
        score_threshold=body.score_threshold,
    )
    inputs = {
        "instruction": body.instruction,
        "n_topics": body.n_topics,
        "max_research_iteration": body.max_research_iteration,
        "option": option,
    }
    config = {
        "configurable": {
            "hf_client": request.app.state.hf_client,
            "openai_client": request.app.state.openai_client,
        }
    }
    return _stream_graph(deep_research_alt_graph, inputs, config, "deep_research_alt_stream")
