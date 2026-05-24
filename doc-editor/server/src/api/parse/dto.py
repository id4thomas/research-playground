"""Parse endpoint DTOs.

요청은 multipart 파일이라 별도 DTO가 없고, 응답은 파싱된 Document를 그대로 반환한다.
프론트엔드가 Document state를 보관하므로 서버는 stateless.
"""
from core.data import Document

__all__ = ["ParseResponse"]

# Document 자체를 응답으로 사용. 별칭으로 의도를 명확히.
ParseResponse = Document
