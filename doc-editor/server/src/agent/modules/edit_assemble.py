"""Shared helpers for converting LLM edit payloads to the API Edit shape."""
from core.data import Block, Edit, InsertEdit, LLMEdit, ReplaceEdit, RewriteEdit

__all__ = ["llm_edit_to_api", "edits_to_map", "enforce_action_rules_map"]


def llm_edit_to_api(le: LLMEdit) -> Edit | None:
    if le.action == "REWRITE" and le.value:
        return RewriteEdit(value=le.value)
    if le.action == "REPLACE" and le.source and le.target:
        return ReplaceEdit(source=le.source, target=le.target)
    if le.action == "INSERT" and le.value:
        return InsertEdit(value=Block(type=le.value_type or "text", content=le.value))
    return None


def edits_to_map(llm_edits: list[LLMEdit]) -> dict[str, list[Edit]]:
    out: dict[str, list[Edit]] = {}
    for le in llm_edits:
        api = llm_edit_to_api(le)
        if api:
            out.setdefault(le.ref, []).append(api)
    return enforce_action_rules_map(out)


def enforce_action_rules_map(edits_map: dict[str, list[Edit]]) -> dict[str, list[Edit]]:
    """ref당 REWRITE는 1개. REWRITE가 있으면 그 ref의 REPLACE/INSERT는 제거."""
    out: dict[str, list[Edit]] = {}
    for ref, lst in edits_map.items():
        rewrites = [e for e in lst if isinstance(e, RewriteEdit)]
        out[ref] = [rewrites[0]] if rewrites else lst
    return out
