from fastapi import APIRouter

from api.chat.dto import ChatRequest, ChatResponse
from api.chat.service import (
    run_answer,
    run_chat,
    run_clarify,
    run_edit,
    run_restructure,
)
from core.dto import ApiRequest, ApiResponse

router = APIRouter()


@router.post("", response_model=ApiResponse[ChatResponse])
async def chat_endpoint(request: ApiRequest[ChatRequest]) -> ApiResponse[ChatResponse]:
    """DocAssistantAgent (intent 분기 포함 통합 파이프라인)"""
    data = await run_chat(request.data)
    return ApiResponse(code=0, message="success", data=data)


@router.post("/edit", response_model=ApiResponse[ChatResponse])
async def edit_endpoint(request: ApiRequest[ChatRequest]) -> ApiResponse[ChatResponse]:
    """doc_editor subgraph"""
    data = await run_edit(request.data)
    return ApiResponse(code=0, message="success", data=data)


@router.post("/restructure", response_model=ApiResponse[ChatResponse])
async def restructure_endpoint(request: ApiRequest[ChatRequest]) -> ApiResponse[ChatResponse]:
    """doc_restructurer subgraph"""
    data = await run_restructure(request.data)
    return ApiResponse(code=0, message="success", data=data)


@router.post("/answer", response_model=ApiResponse[ChatResponse])
async def answer_endpoint(request: ApiRequest[ChatRequest]) -> ApiResponse[ChatResponse]:
    """doc_answerer subgraph"""
    data = await run_answer(request.data)
    return ApiResponse(code=0, message="success", data=data)


@router.post("/clarify", response_model=ApiResponse[ChatResponse])
async def clarify_endpoint(request: ApiRequest[ChatRequest]) -> ApiResponse[ChatResponse]:
    """doc_clarifier subgraph"""
    data = await run_clarify(request.data)
    return ApiResponse(code=0, message="success", data=data)
