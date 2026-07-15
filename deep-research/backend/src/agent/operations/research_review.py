from openai import AsyncOpenAI
from pydantic import BaseModel

from agent.base import BaseOperation
from agent.data.paper import PaperRetrievalData


class ReviewResult(BaseModel):
    sufficient: bool
    review: str
    followup_topics: list[str]

INSTRUCTION = '''유저의 관심사에 대해 지금까지 탐색한 토픽들과 수집된 논문들을 검토합니다.
1. sufficient: 수집된 논문들이 관심사를 충분히 다루고 있는지 평가합니다
2. review: 어떤 부분이 잘 커버되었고 어떤 부분이 부족한지 간략히 작성합니다
3. followup_topics: 충분하지 않다면 추가로 찾아볼만한 새로운 검색 토픽을 최대 {max_topics}개 생성합니다 (충분하면 빈 리스트)
   - 이미 탐색한 토픽과 겹치지 않아야 합니다
   - 각 토픽은 간결한 자연어 구(phrase) 하나로 작성하고, AND/OR 등 불리언 연산자나 따옴표, 괄호는 절대 사용하지 않습니다
다음 JSON 형식으로 반환합니다
{{"sufficient": bool, "review": str, "followup_topics": list[str]}}'''

# MODEL="Qwen3.6-27B"
MODEL="Qwen3.6-35B-A3B"
PARAMS={
    "top_p": 0.8,
    "temperature": 0.7,
    # vLLM 확장 파라미터는 extra_body로 전달해야 함
    # repetition_penalty 1.5는 생성 폭주(degeneration)를 유발해 낮게 설정
    "extra_body": {"repetition_penalty": 1.05}
}


def _format_papers(retrieved: list[PaperRetrievalData]) -> str:
    lines = []
    for r in retrieved:
        lines.append(f"- [{r.source_topic}] {r.data.title}: {r.data.summary[:300]}")
    return "\n".join(lines) if lines else "(없음)"


class ResearchReviewOperation(BaseOperation):
    @classmethod
    async def run(
        cls,
        client: AsyncOpenAI,
        instruction: str,
        topics: list[str],
        retrieved: list[PaperRetrievalData],
        max_topics: int = 3,
    ) -> ReviewResult:
        topics_str = "\n".join(f"- {t}" for t in topics)
        messages = [
            {"role": "user", "content": INSTRUCTION.format(max_topics=max_topics)},
            {
                "role": "user",
                "content": (
                    f"관심사: {instruction}\n\n"
                    f"탐색한 토픽:\n{topics_str}\n\n"
                    f"수집된 논문:\n{_format_papers(retrieved)}"
                )
            }
        ]

        completion = await client.chat.completions.parse(
            model=MODEL,
            messages=messages,
            response_format=ReviewResult,
            **PARAMS
        )
        return completion.choices[0].message.parsed
