from openai import AsyncOpenAI
from pydantic import BaseModel

from agent.base import BaseOperation


class QueryResult(BaseModel):
    query: str

INSTRUCTION = '''주어진 토픽의 논문을 검색하기 위한 검색 쿼리를 생성합니다.
다음 JSON 형식으로 반환합니다
{"query": str}'''

MODEL="Qwen3.6-27B"
PARAMS={
    "top_p": 0.8,
    "temperature": 0.7,
    # vLLM 확장 파라미터는 extra_body로 전달해야 함
    "extra_body": {"repetition_penalty": 1.5}
}

class QueryGenerationOperation(BaseOperation):
    @classmethod
    async def run(cls, client: AsyncOpenAI, topic: str) -> str:
        messages = [
            {"role": "user", "content": INSTRUCTION},
            {"role": "user", "content": f"토픽: {topic}"}
        ]
        
        completion = await client.chat.completions.parse(
            model=MODEL,
            messages=messages,
            response_format=QueryResult,
            **PARAMS
        )
        result = completion.choices[0].message.parsed
        return result.query