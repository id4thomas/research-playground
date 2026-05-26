"""POST /api/parse 테스트.

이전 버전의 /api/documents/upload + /api/documents/{doc_id}는 단일 stateless
/api/parse 엔드포인트로 통합되었다. 응답은 ApiResponse 엔벨로프로 감싸 반환된다.
"""
from tests.conftest import SAMPLE_MD, unwrap


def test_parse_returns_document(client):
    resp = client.post(
        "/api/parse",
        files={"file": ("sample.md", SAMPLE_MD.encode(), "text/markdown")},
    )
    assert resp.status_code == 200
    body = unwrap(resp)
    assert "sections" in body
    assert "outline" in body
    assert isinstance(body["outline"], list)
    assert len(body["outline"]) > 0
    assert len(body["sections"]) > 0


def test_parse_outline_has_required_fields(client):
    resp = client.post(
        "/api/parse",
        files={"file": ("sample.md", SAMPLE_MD.encode(), "text/markdown")},
    )
    outline = unwrap(resp)["outline"]
    for item in outline:
        assert "code" in item
        assert "title" in item
        assert "level" in item
