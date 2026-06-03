"""Markdown → Document parser using docling."""
from __future__ import annotations

import re
from typing import Optional

from core.data import Block, Document, Section, SectionMeta, make_block


def _assign_section_codes(headers: list[tuple[int, str]]) -> list[tuple[str, int, str]]:
    """
    headers: [(level, title), ...]  (level: 1=H1, 2=H2, ...)
    returns: [(code, level, title), ...]  e.g. ("S1-2-1", 3, "세부 내용")
    """
    counters: list[int] = []
    result = []
    for level, title in headers:
        if level > len(counters):
            while len(counters) < level:
                counters.append(0)
        else:
            counters = counters[:level]
            while len(counters) < level:
                counters.append(0)
        counters[level - 1] += 1
        code = "S" + "-".join(str(c) for c in counters)
        result.append((code, level, title))
    return result


def _split_into_blocks(text: str) -> list[Block]:
    """Split section body text into blocks (text/equation/table)."""
    blocks: list[Block] = []
    current_lines: list[str] = []

    def flush_text():
        content = "\n".join(current_lines).strip()
        if content:
            blocks.append(make_block("text", content))
        current_lines.clear()

    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        # Detect equation block ($$...$$)
        if line.strip().startswith("$$"):
            flush_text()
            eq_lines = [line]
            i += 1
            while i < len(lines) and not lines[i].strip().endswith("$$"):
                eq_lines.append(lines[i])
                i += 1
            if i < len(lines):
                eq_lines.append(lines[i])
            blocks.append(make_block("equation", "\n".join(eq_lines)))
        # Detect HTML table
        elif line.strip().startswith("<table"):
            flush_text()
            table_lines = [line]
            i += 1
            while i < len(lines) and "</table>" not in lines[i]:
                table_lines.append(lines[i])
                i += 1
            if i < len(lines):
                table_lines.append(lines[i])
            blocks.append(make_block("table", "\n".join(table_lines)))
        elif line.strip() == "":
            flush_text()
        else:
            current_lines.append(line)
        i += 1

    flush_text()
    return blocks


def _make_section(meta: SectionMeta, blocks: list[Block]) -> Section:
    """블록 리스트를 (blocks dict, order) 형태의 Section으로 조립."""
    return Section(
        meta=meta,
        blocks={b.id: b for b in blocks},
        order=[b.id for b in blocks],
    )


def parse_markdown(md_text: str) -> Document:
    """Parse a Markdown string into a Document with auto-assigned section codes."""
    # Split into (header_line, body) pairs
    header_pattern = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
    matches = list(header_pattern.finditer(md_text))

    if not matches:
        # No headers — treat entire doc as single section S1
        meta = SectionMeta(code="S1", title="Document", level=1)
        return Document(
            sections={"S1": _make_section(meta, _split_into_blocks(md_text))},
            outline=[meta],
        )

    headers = [(len(m.group(1)), m.group(2).strip()) for m in matches]
    coded = _assign_section_codes(headers)

    sections: dict[str, Section] = {}
    outline_flat: list[SectionMeta] = []

    for idx, (code, level, title) in enumerate(coded):
        start = matches[idx].end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(md_text)
        body = md_text[start:end]
        blocks = _split_into_blocks(body)
        meta = SectionMeta(code=code, title=title, level=level)
        sections[code] = _make_section(meta, blocks)
        outline_flat.append(meta)

    # Populate children
    code_to_meta = {m.code: m for m in outline_flat}
    for i, meta in enumerate(outline_flat):
        for other in outline_flat[i + 1:]:
            if other.level == meta.level + 1:
                meta.children.append(other.code)
            elif other.level <= meta.level:
                break

    return Document(sections=sections, outline=outline_flat)
