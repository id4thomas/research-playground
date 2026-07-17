from contextlib import asynccontextmanager
import os

# 자동 패치(APM 활성화) 차단
os.environ["DD_APM_TRACING_ENABLED"] = "false"
os.environ["DD_PROFILING_STACK_ENABLED"] = "false"
os.environ["DD_TRACE_AUTO_PATCH"] = "false"
os.environ["DD_INSTRUMENTATION_TELEMETRY_ENABLED"] = "false"

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from openai import AsyncOpenAI

from ddtrace import patch
from ddtrace.llmobs import LLMObs

from api.router import router
from client.huggingface import HuggingfacePapersClient
from config import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 그래프 노드들에 RunnableConfig(configurable)로 주입되는 client들
    app.state.openai_client = AsyncOpenAI(
        base_url=settings.llm.base_url, api_key=settings.llm.api_key
    )
    app.state.hf_client = HuggingfacePapersClient()
    
    if settings.tracing.enabled:
        # The fastapi integration is enabled automatically when using
        patch(openai=False, fastapi=False, langchain=True)  # 직접 정의한 span 외 로깅 방지
        LLMObs.enable(
            ml_app=settings.tracing.app,
            api_key=settings.tracing.api_key,
            site=settings.tracing.site,
            agentless_enabled=True,
        )
    
    yield
    await app.state.openai_client.close()
    await app.state.hf_client.aclose()


app = FastAPI(lifespan=lifespan)
# 데모 페이지(정적 파일 서버)에서의 호출 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)
