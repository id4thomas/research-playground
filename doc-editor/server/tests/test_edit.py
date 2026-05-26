"""POST /api/edit 테스트."""
from tests.conftest import make_chat_payload, unwrap


def test_edit_returns_edits(client, uploaded_doc):
    doc_id, document = uploaded_doc
    payload = make_chat_payload(doc_id, document, "문제점 섹션의 내용을 좀 더 구체적으로 보완해줘")

    resp = client.post("/api/chat/edit", json=payload)
    assert resp.status_code == 200
    body = unwrap(resp)
    assert body["intent"] == "edit"
    assert body["message"]["role"] == "assistant"
    assert isinstance(body["edits"], dict)
    assert len(body["edits"]) > 0, "edits가 비어 있음 — 수정안이 생성되지 않음"


def test_edit_with_selected_blocks(client, uploaded_doc):
    doc_id, document = uploaded_doc
    first_section_code = list(document["sections"].keys())[0]
    selected = [f"{first_section_code};0"]

    payload = make_chat_payload(
        doc_id, document, "선택한 블록을 더 간결하게 다시 써줘", selected=selected
    )
    resp = client.post("/api/chat/edit", json=payload)
    assert resp.status_code == 200
    body = unwrap(resp)
    assert body["intent"] == "edit"
    assert len(body["edits"]) > 0


def test_edit_response_shape(client, uploaded_doc):
    doc_id, document = uploaded_doc
    payload = make_chat_payload(doc_id, document, "해결 수단 섹션을 보완해줘")

    resp = client.post("/api/chat/edit", json=payload)
    body = unwrap(resp)

    for ref, edits in body["edits"].items():
        assert isinstance(ref, str)
        assert ";" in ref, f"ref '{ref}'에 ';' 없음 — 블록 ref 형식 오류"
        assert isinstance(edits, list)
        for edit in edits:
            assert "action" in edit
            assert edit["action"] in ("REWRITE", "REPLACE", "INSERT")


def test_edit_message_no_internal_codes(client, uploaded_doc):
    """응답 메시지에 내부 섹션 코드(S1, S1-2;0 등)가 노출되지 않아야 함."""
    import re
    doc_id, document = uploaded_doc
    payload = make_chat_payload(doc_id, document, "종래 기술 섹션을 수정해줘")

    resp = client.post("/api/chat/edit", json=payload)
    message_content = unwrap(resp)["message"]["content"]
    codes = re.findall(r"\bS\d+(?:-\d+)*(?:;\d+)?\b", message_content)
    assert not codes, f"응답 메시지에 내부 코드 노출됨: {codes}"
