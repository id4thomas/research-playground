from openai.types.chat import ChatCompletion
from openai.types.completion_usage import CompletionUsage
from pydantic import BaseModel, Field


class TokenUsage(BaseModel):
    """LLM 호출 1회(또는 누적)의 토큰 사용량.
    - total_tokens: input+output
    - prompt_tokens: input tokens
    - completion_tokens: output tokens (reasoning 미포함 순수 출력)
    - details: 원본 usage 딕셔너리 모음 (k: 구분용 명칭, v: usage 딕셔너리)
    """

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    details: dict[str, dict] = Field(default_factory=dict)

    def add(self, other: "TokenUsage | None") -> "TokenUsage":
        if other is None:
            return self
        return TokenUsage(
            prompt_tokens=self.prompt_tokens + other.prompt_tokens,
            completion_tokens=self.completion_tokens + other.completion_tokens,
            total_tokens=self.total_tokens + other.total_tokens,
            details={**self.details, **other.details},
        )

    @classmethod
    def from_chat_completion(cls, response: ChatCompletion, name: str) -> "TokenUsage":
        # https://github.com/openai/openai-python/blob/e20b6b82c145091f0d8412a7e4a9bc5900a40462/src/openai/types/completion_usage.py#L44-L60
        usage: CompletionUsage = response.usage

        completion_tokens = usage.completion_tokens
        prompt_tokens = usage.prompt_tokens
        total_tokens = usage.total_tokens
        return cls(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            details={name: usage.model_dump()},
        )