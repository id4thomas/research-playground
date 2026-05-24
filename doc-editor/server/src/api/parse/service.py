"""Parse service — Markdown bytes → Document."""
from api.parse.dto import ParseResponse
from api.parse.md_parser import parse_markdown


async def parse_markdown_bytes(content: bytes) -> ParseResponse:
    md_text = content.decode("utf-8")
    return parse_markdown(md_text)
