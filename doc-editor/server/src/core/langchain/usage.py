"""Token usage tracking — extract from LangChain AIMessage and aggregate."""
from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage
from pydantic import BaseModel


class TokenUsage(BaseModel):
    """LLM 호출 1회(또는 누적)의 토큰 사용량.

    - input:     prompt tokens
    - output:    completion tokens (reasoning 미포함 순수 출력)
    - reasoning: 모델이 내부적으로 생성한 thinking/reasoning 토큰
    """
    input: int = 0
    output: int = 0
    total: int = 0
    reasoning: int = 0

    def add(self, other: "TokenUsage | None") -> "TokenUsage":
        if other is None:
            return self
        return TokenUsage(
            input=self.input + other.input,
            output=self.output + other.output,
            total=self.total + other.total,
            reasoning=self.reasoning + other.reasoning,
        )

    @classmethod
    def from_message(cls, msg: AIMessage) -> "TokenUsage":
        """LangChain AIMessage에서 추출.
        usage_metadata example
        {
            'input_tokens': 27,
            'output_tokens': 25,
            'total_tokens': 52,
            'input_token_details': {},
            'output_token_details': {}
        }
        """
        if msg is None:
            return cls()
        um = getattr(msg, "usage_metadata", None)
        if um:
            input_tokens = int(um.get("input_tokens", 0) or 0)
            output_tokens = int(um.get("output_tokens", 0) or 0)
            total_tokens = int(um.get("total_tokens", 0) or 0)
            
            details = um.get("output_token_details") or {}
            reasoning_tokens = int(details.get("reasoning", 0) or 0)

            return cls(
                input=input_tokens,
                output=output_tokens,
                total=total_tokens,
                reasoning=reasoning_tokens
            )
        else:
            return cls()
        
        # msg.usage
        
        # # include_raw=True 응답은 {"raw": AIMessage, "parsed": ..., "parsing_error": ...}
        # if isinstance(msg, dict) and "raw" in msg:
        #     msg = msg.get("raw")
        # if msg is None:
        #     return cls()
        #     )
        # rm = getattr(msg, "response_metadata", None) or {}
        # tu = rm.get("token_usage") or {}
        # if tu:
        #     details = tu.get("completion_tokens_details") or {}
        #     return cls(
        #         input=int(tu.get("prompt_tokens", 0) or 0),
        #         output=int(tu.get("completion_tokens", 0) or 0),
        #         total=int(tu.get("completion_tokens", 0) or 0),
        #         reasoning=int(details.get("reasoning_tokens", 0) or 0),
        #     )
        # return cls()
