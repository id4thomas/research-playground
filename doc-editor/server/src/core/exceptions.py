"""Application-level exceptions.

jarvis-patent-api 패턴을 차용 — main.py의 exception handler가 이 타입을 잡아
표준 ApiResponse 포맷(code/message/data)으로 변환한다.

코드 체계
- 1000: UnknownAPIError (fallback)
- 2000: LLMAPIError
- 2010: LLMTimeoutError
- 3000: GraphExecutionError  (LangGraph 자체 실패)
"""
import json


__all__ = [
    "APIError",
    "LLMAPIError",
    "LLMTimeoutError",
    "GraphExecutionError",
]


class APIError(Exception):
    message: str

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class LLMAPIError(APIError):
    model: str

    def __init__(self, message: str, model: str = ""):
        super().__init__(message=message)
        self.model = model

    def __str__(self) -> str:
        msg = json.dumps({"model": self.model, "message": self.message})
        return f"[LLMAPIError] {msg}"


class LLMTimeoutError(LLMAPIError):
    inf_time: float = 0.0

    def __init__(self, model: str = "", inf_time: float = 0.0):
        super().__init__("API Timeout Error", model=model)
        self.inf_time = inf_time

    def __str__(self) -> str:
        msg = json.dumps(
            {"model": self.model, "time": f"{self.inf_time:.4f}", "message": self.message}
        )
        return f"[LLMTimeoutError] {msg}"


class GraphExecutionError(APIError):
    """LangGraph 실행 중 발생한 비-LLM 실패."""

    graph: str

    def __init__(self, message: str, graph: str = ""):
        super().__init__(message=message)
        self.graph = graph

    def __str__(self) -> str:
        msg = json.dumps({"graph": self.graph, "message": self.message})
        return f"[GraphExecutionError] {msg}"
