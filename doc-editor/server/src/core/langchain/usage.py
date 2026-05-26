"""Token usage tracking — extract from LangChain AIMessage and aggregate."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class TokenUsage(BaseModel):
    """LLM 호출 1회(또는 누적)의 토큰 사용량.

    - input:     prompt tokens
    - output:    completion tokens (reasoning 미포함 순수 출력)
    - reasoning: 모델이 내부적으로 생성한 thinking/reasoning 토큰
    """
    input: int = 0
    output: int = 0
    reasoning: int = 0

    def add(self, other: "TokenUsage | None") -> "TokenUsage":
        if other is None:
            return self
        return TokenUsage(
            input=self.input + other.input,
            output=self.output + other.output,
            reasoning=self.reasoning + other.reasoning,
        )

    @classmethod
    def from_message(cls, msg: Any) -> "TokenUsage":
        """LangChain AIMessage(또는 with_structured_output include_raw dict)에서 추출."""
        if msg is None:
            return cls()
        # include_raw=True 응답은 {"raw": AIMessage, "parsed": ..., "parsing_error": ...}
        if isinstance(msg, dict) and "raw" in msg:
            msg = msg.get("raw")
        if msg is None:
            return cls()
        um = getattr(msg, "usage_metadata", None)
        if um:
            details = um.get("output_token_details") or {}
            out = int(um.get("output_tokens", 0) or 0)
            reasoning = int(details.get("reasoning", 0) or 0)
            pure_out = max(0, out - reasoning)
            return cls(
                input=int(um.get("input_tokens", 0) or 0),
                output=pure_out,
                reasoning=reasoning,
            )
        rm = getattr(msg, "response_metadata", None) or {}
        tu = rm.get("token_usage") or {}
        if tu:
            details = tu.get("completion_tokens_details") or {}
            return cls(
                input=int(tu.get("prompt_tokens", 0) or 0),
                output=int(tu.get("completion_tokens", 0) or 0),
                reasoning=int(details.get("reasoning_tokens", 0) or 0),
            )
        return cls()
