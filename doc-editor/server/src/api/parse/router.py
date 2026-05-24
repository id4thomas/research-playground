"""Parse router — POST /api/parse: upload .md, return parsed Document."""
from fastapi import APIRouter, File, UploadFile

from api.parse.dto import ParseResponse
from api.parse.service import parse_markdown_bytes
from core.dto import ApiResponse

router = APIRouter()


@router.post("", response_model=ApiResponse[ParseResponse])
async def parse_endpoint(file: UploadFile = File(...)) -> ApiResponse[ParseResponse]:
    content = await file.read()
    document = await parse_markdown_bytes(content)
    return ApiResponse(code=0, message="success", data=document)
