"""POST /api/restructure 테스트."""
from tests.conftest import make_chat_payload, unwrap

VALID_ACTIONS = ("RENAME", "ADD", "REMOVE", "MERGE")


def test_restructure_add_section(client, uploaded_doc):
    doc_id, document = uploaded_doc
    payload = make_chat_payload(doc_id, document, "발명의 효과 섹션 아래에 '적용 사례' 섹션을 추가해줘")

    resp = client.post("/api/chat/restructure", json=payload)
    assert resp.status_code == 200
    body = unwrap(resp)
    assert body["intent"] == "restructure"
    assert isinstance(body["outline_actions"], list)
    assert len(body["outline_actions"]) > 0


def test_restructure_rename_section(client, uploaded_doc):
    doc_id, document = uploaded_doc
    payload = make_chat_payload(doc_id, document, "종래 기술 섹션 이름을 '기존 기술 현황'으로 변경해줘")

    resp = client.post("/api/chat/restructure", json=payload)
    assert resp.status_code == 200
    body = unwrap(resp)
    assert body["intent"] == "restructure"
    assert len(body["outline_actions"]) > 0
    actions = [a["action"] for a in body["outline_actions"]]
    assert "RENAME" in actions


def test_restructure_action_shape(client, uploaded_doc):
    doc_id, document = uploaded_doc
    payload = make_chat_payload(doc_id, document, "문제점 섹션을 삭제해줘")

    resp = client.post("/api/chat/restructure", json=payload)
    body = unwrap(resp)

    for action in body["outline_actions"]:
        assert "action" in action
        assert action["action"] in VALID_ACTIONS


def test_restructure_no_edits(client, uploaded_doc):
    """restructure 응답에는 블록 edits가 없어야 함."""
    doc_id, document = uploaded_doc
    payload = make_chat_payload(doc_id, document, "핵심 구성 섹션 이름을 '주요 구성'으로 바꿔줘")

    resp = client.post("/api/chat/restructure", json=payload)
    body = unwrap(resp)
    assert body["edits"] == {} or body["edits"] is None or not body["edits"]
