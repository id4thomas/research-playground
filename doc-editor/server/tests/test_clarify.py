"""POST /api/clarify 테스트."""
from tests.conftest import make_chat_payload, unwrap


def test_clarify_returns_question(client, uploaded_doc):
    doc_id, document = uploaded_doc
    payload = make_chat_payload(doc_id, document, "좀 고쳐줘")

    resp = client.post("/api/chat/clarify", json=payload)
    assert resp.status_code == 200
    body = unwrap(resp)
    assert body["intent"] == "clarify"
    assert len(body["message"]["content"]) > 0


def test_clarify_options_are_list(client, uploaded_doc):
    doc_id, document = uploaded_doc
    payload = make_chat_payload(doc_id, document, "뭔가 수정해줘")

    resp = client.post("/api/chat/clarify", json=payload)
    body = unwrap(resp)
    options = body.get("clarify_options", [])
    assert isinstance(options, list)


def test_clarify_no_edits(client, uploaded_doc):
    """clarify 응답에는 edits/outline_actions가 없어야 함."""
    doc_id, document = uploaded_doc
    payload = make_chat_payload(doc_id, document, "어떻게 할까요?")

    resp = client.post("/api/chat/clarify", json=payload)
    body = unwrap(resp)
    assert not body.get("edits")
    assert not body.get("outline_actions")
