"""Shared fixtures for API integration tests.

사용자 승인 및 로컬 서버 기동 이슈를 방지하기 위해, FastAPI TestClient를 사용하여 
별도의 서버 기동 없이 테스트를 인프로세스(in-process)로 수행합니다.
"""
import sys
import os
import pytest
import httpx

# src 디렉토리를 path에 추가하여 main 모듈 임포트 가능하도록 설정
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from main import app
from fastapi.testclient import TestClient

BASE_URL = "http://localhost:5000"

SAMPLE_MD = """\
# 배경기술

## 종래 기술

종래의 문서 관리 시스템은 수작업에 의존하여 비효율성이 높았다.
특히 대용량 문서에서 특정 섹션을 탐색하는 데 많은 시간이 소요되었다.

## 문제점

기존 방식의 주요 문제점은 다음과 같다.
첫째, 버전 관리가 어렵다. 둘째, 협업 시 충돌이 자주 발생한다.

# 해결 수단

## 핵심 구성

본 발명은 AI 기반 문서 편집 에이전트를 도입하여 위 문제를 해결한다.

# 발명의 효과

본 발명에 의하면 문서 편집 시간을 60% 이상 단축할 수 있다.
"""


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def uploaded_doc(client):
    """샘플 Markdown 파싱 후 (project_id, document) 반환.

    서버는 더 이상 Document를 저장하지 않는다 — 프론트엔드가 state를 관리하므로
    여기서는 fixture가 클라이언트 역할을 흉내내 파싱 결과를 보관한다.
    project_id는 클라이언트가 자유롭게 부여하는 값이라 임의 문자열을 사용.
    """
    resp = client.post(
        "/api/parse",
        files={"file": ("test.md", SAMPLE_MD.encode(), "text/markdown")},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # ApiResponse 엔벨로프에서 실제 Document를 꺼낸다.
    document = body["data"]
    return "test-project", document


def make_chat_payload(doc_id: str, document: dict, user_message: str, selected: list[str] | None = None) -> dict:
    """ApiRequest 엔벨로프로 감싼 chat payload를 만든다."""
    return {
        "data": {
            "project_id": doc_id,
            "messages": [{"role": "user", "content": user_message}],
            "document": document,
            "selected": selected,
        }
    }


def unwrap(resp) -> dict:
    """ApiResponse 엔벨로프에서 data를 꺼낸다. 실패 시 raise."""
    body = resp.json()
    assert body.get("code") == 0, f"non-zero code: {body}"
    return body["data"] or {}
