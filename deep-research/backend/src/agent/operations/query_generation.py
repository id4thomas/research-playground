import re

from openai import AsyncOpenAI
from pydantic import BaseModel

from agent.base import BaseOperation


class QueryResult(BaseModel):
    query: str

INSTRUCTION = '''주어진 토픽의 논문을 검색하기 위한 검색 쿼리를 생성합니다.
검색 엔진은 시맨틱+전문(full-text) 하이브리드 검색입니다 (Huggingface Papers).
논문 제목처럼 읽히는 하나의 짧은 영어 구(phrase)를 생성하세요.

규칙:
- 반드시 영어로 작성합니다 (영어가 아니면 검색 결과가 나오지 않습니다)
- 3~8 단어의 명사구 하나만 작성합니다. 문장, 질문, 나열식 조합은 금지입니다
- 소문자 단어와 표준 약어(RAG, LLM 등)만 사용합니다
- 다음 문자는 절대 사용하지 않습니다: 괄호 () , 따옴표 "" , 쉼표, 슬래시, 하이픈 이외의 기호
- AND, OR, NOT 같은 불리언 연산자는 검색 문법으로 지원되지 않으므로 절대 사용하지 않습니다
- 여러 개념을 다 담으려 하지 말고, 토픽의 핵심 하나에 집중합니다

좋은 예:
- retrieval augmented generation medical diagnosis
- knowledge graph RAG healthcare
- LLM bias clinical decision making

나쁜 예 (절대 금지):
- (RAG OR Retrieval-Augmented Generation) healthcare challenges  ← 괄호/OR 사용
- "medical" AND "RAG"  ← 따옴표/AND 사용
- healthcare diagnostic reasoning challenges and biases in RAG systems and LLMs  ← 너무 길고 나열식

다음 JSON 형식으로 반환합니다
{"query": str}'''

# MODEL="Qwen3.6-27B"
MODEL="Qwen3.6-35B-A3B"
PARAMS={
    "top_p": 0.8,
    # 지시사항 준수를 위해 낮은 temperature 사용 (재검색 시 다양성은 top_p로 확보)
    "temperature": 0.3,
    # vLLM 확장 파라미터는 extra_body로 전달해야 함
    "extra_body": {"repetition_penalty": 1.5}
}

def _sanitize_query(query: str, max_chars: int = 250) -> str:
    """HF 검색 API 제약 대응: q는 250자 초과 시 400. 불리언 문법은 미지원이므로 제거"""
    query = re.sub(r'["\'()\[\]{}+*:]', " ", query)
    query = re.sub(r"\b(AND|OR|NOT)\b", " ", query)
    query = re.sub(r"\s+", " ", query).strip()
    if len(query) > max_chars:
        # 단어 경계에서 자름
        query = query[:max_chars].rsplit(" ", 1)[0]
    return query


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
        return _sanitize_query(result.query)