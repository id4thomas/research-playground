from ddtrace.llmobs import LLMObs
from fastapi import APIRouter, Request

from agent.data.search_option import SearchOption
from agent.graphs.hf_paper_search.graph import graph

from api.dto import PaperResult, SearchRequest, SearchResponse

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
