"""Strip leaked internal section/block codes (S1, S1-2;0) from user-facing text."""
import re

from core.data import Document

_REF_PATTERN = re.compile(r"(?<![A-Za-z0-9])S\d+(?:-\d+)*(?:;\d+)?")


def strip_section_codes(message: str, doc: Document) -> str:
    if not message:
        return message
    title_of = {code: section.meta.title for code, section in doc.sections.items()}

    def _sub(match: re.Match) -> str:
        token = match.group(0)
        code = token.split(";", 1)[0]
        title = title_of.get(code)
        return f"'{title}'" if title else token

    return _REF_PATTERN.sub(_sub, message)
