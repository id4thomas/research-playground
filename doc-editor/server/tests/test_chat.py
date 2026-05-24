"""POST /api/chat (orchestrator routing) 테스트."""
import re

from tests.conftest import make_chat_payload, unwrap

VALID_INTENTS = {"edit", "restructure", "clarify", "answer"}


def test_chat_routes_edit_intent(client, uploaded_doc):
    doc_id, document = uploaded_doc
    payload = make_chat_payload(doc_id, document, "문제점 섹션 내용을 더 구체적으로 수정해줘")

    resp = client.post("/api/chat", json=payload)
    assert resp.status_code == 200
    body = unwrap(resp)
    assert body["intent"] in VALID_INTENTS
    assert body["intent"] == "edit", f"edit으로 라우팅 기대, 실제: {body['intent']}"


def test_chat_routes_restructure_intent(client, uploaded_doc):
    doc_id, document = uploaded_doc
    payload = make_chat_payload(doc_id, document, "배경기술 섹션 아래에 '선행 연구' 섹션을 추가해줘")

    resp = client.post("/api/chat", json=payload)
    assert resp.status_code == 200
    body = unwrap(resp)
    assert body["intent"] == "restructure", f"restructure으로 라우팅 기대, 실제: {body['intent']}"


def test_chat_routes_answer_intent(client, uploaded_doc):
    doc_id, document = uploaded_doc
    payload = make_chat_payload(doc_id, document, "이 문서에서 말하는 발명의 효과가 뭐야?")

    resp = client.post("/api/chat", json=payload)
    assert resp.status_code == 200
    body = unwrap(resp)
    assert body["intent"] == "answer", f"answer으로 라우팅 기대, 실제: {body['intent']}"


def test_chat_response_shape(client, uploaded_doc):
    doc_id, document = uploaded_doc
    payload = make_chat_payload(doc_id, document, "종래 기술 내용을 보완해줘")

    resp = client.post("/api/chat", json=payload)
    body = unwrap(resp)
    assert "message" in body
    assert "intent" in body
    assert body["intent"] in VALID_INTENTS
    assert "edits" in body
    assert "outline_actions" in body


def test_chat_no_internal_codes_in_message(client, uploaded_doc):
    doc_id, document = uploaded_doc
    payload = make_chat_payload(doc_id, document, "핵심 구성 섹션을 자세히 설명해줘")

    resp = client.post("/api/chat", json=payload)
    content = unwrap(resp)["message"]["content"]
    codes = re.findall(r"\bS\d+(?:-\d+)*(?:;\d+)?\b", content)
    assert not codes, f"내부 코드 노출됨: {codes}"


def test_chat_with_selected_blocks(client, uploaded_doc):
    doc_id, document = uploaded_doc
    first_code = list(document["sections"].keys())[0]
    selected = [f"{first_code};0"]

    payload = make_chat_payload(doc_id, document, "선택한 부분을 간결하게 다시 써줘", selected=selected)
    resp = client.post("/api/chat", json=payload)
    assert resp.status_code == 200
    body = unwrap(resp)
    # selected가 있으면 clarify가 아닌 edit으로 라우팅
    assert body["intent"] != "clarify"
