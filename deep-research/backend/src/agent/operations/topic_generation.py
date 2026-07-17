from openai import AsyncOpenAI
from pydantic import BaseModel, Field, create_model

from agent.base import BaseOperation


INSTRUCTION = '''유저의 관심사를 바탕으로 논문을 검색하기 위한 검색 토픽을 {n}개 생성합니다.
- 각 토픽은 관심사와 관련 있되 서로 겹치지 않도록 다양하게 작성합니다
- 각 토픽은 간결한 자연어 구(phrase) 하나로 작성합니다 (예: "graph 기반 RAG의 의료 진단 활용")
- AND, OR 같은 불리언 연산자나 따옴표, 괄호 등 검색 문법은 절대 사용하지 않습니다
다음 JSON 형식으로 반환합니다
{{"topics": list[str]}}'''

# MODEL="Qwen3.6-27B"
MODEL="Qwen3.6-35B-A3B"
PARAMS={
    "top_p": 0.8,
    "temperature": 0.7,
    # vLLM 확장 파라미터는 extra_body로 전달해야 함
    # repetition_penalty 1.5는 생성 폭주(degeneration)를 유발해 낮게 설정
    "extra_body": {"repetition_penalty": 1.05}
}


def _build_result_model(n: int) -> type[BaseModel]:
    # n을 구조화 생성 스키마의 리스트 길이 제약으로 반영
    return create_model(
        "TopicResult",
        topics=(list[str], Field(min_length=n, max_length=n)),
    )


class TopicGenerationOperation(BaseOperation):
    @classmethod
    async def run(cls, client: AsyncOpenAI, instruction: str, n: int) -> list[str]:
        messages = [
            {"role": "user", "content": INSTRUCTION.format(n=n)},
            {"role": "user", "content": f"관심사: {instruction}"}
        ]

        completion = await client.chat.completions.parse(
            model=MODEL,
            messages=messages,
            response_format=_build_result_model(n),
            **PARAMS
        )
        result = completion.choices[0].message.parsed
        return result.topics
