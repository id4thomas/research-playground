"""POST /api/answer 테스트."""
import re

from tests.conftest import make_chat_payload, unwrap


def test_answer_returns_message(client, uploaded_doc):
    doc_id, document = uploaded_doc
    payload = make_chat_payload(doc_id, document, "이 문서는 어떤 내용을 다루고 있어?")

    resp = client.post("/api/chat/answer", json=payload)
    assert resp.status_code == 200
    body = unwrap(resp)
    assert body["intent"] == "answer"
    assert body["message"]["role"] == "assistant"
    assert len(body["message"]["content"]) > 0


def test_answer_no_edits(client, uploaded_doc):
    """answer 응답에는 edits가 없어야 함."""
    doc_id, document = uploaded_doc
    payload = make_chat_payload(doc_id, document, "발명의 효과를 요약해줘")

    resp = client.post("/api/chat/answer", json=payload)
    body = unwrap(resp)
    assert not body.get("edits")
    assert not body.get("outline_actions")


def test_answer_no_internal_codes(client, uploaded_doc):
    """응답 메시지에 내부 섹션 코드가 노출되지 않아야 함."""
    doc_id, document = uploaded_doc
    payload = make_chat_payload(doc_id, document, "각 섹션의 주요 내용을 설명해줘")

    resp = client.post("/api/chat/answer", json=payload)
    content = unwrap(resp)["message"]["content"]
    codes = re.findall(r"\bS\d+(?:-\d+)*(?:;\d+)?\b", content)
    assert not codes, f"내부 코드 노출됨: {codes}"


def test_answer_is_korean(client, uploaded_doc):
    """응답이 한국어를 포함해야 함 (한글 문자 존재 여부로 확인)."""
    doc_id, document = uploaded_doc
    payload = make_chat_payload(doc_id, document, "문서의 핵심 내용이 뭐야?")

    resp = client.post("/api/chat/answer", json=payload)
    content = unwrap(resp)["message"]["content"]
    assert re.search(r"[가-힣]", content), "응답에 한국어가 없음"
