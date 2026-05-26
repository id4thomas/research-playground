"""Prompt + model-config bundles loaded from YAML.

각 에이전트는 `agent/modules/prompts/<name>.yaml`에서 시스템 프롬프트, 모델 설정,
선택적인 output_schema(dotted path)를 함께 관리한다. 호출 측은 `load_agent_spec(name)`로
`AgentSpec`을 받아 `render_system(**vars)`로 시스템 프롬프트를 만들고
`spec.model_kwargs`를 `LangChainChatModel.get_model`에 그대로 넘긴다.

순환 임포트를 피하기 위해 spec 로딩은 호출 시점에 lazy로 일어나고, 결과는 lru_cache로
프로세스당 1회만 수행된다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from importlib import import_module
from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, StrictUndefined

_DIR = Path(__file__).resolve().parent.parent / "prompts"
_JINJA = Environment(undefined=StrictUndefined, keep_trailing_newline=True)


HISTORY_FORMAT_NOTE = """\
[대화 히스토리 포맷]
각 메시지에는 다음 태그가 붙어 있습니다:
  - [ASSISTANT · 편집 제안] / [ASSISTANT · 사용자에게 질문] / [ASSISTANT · 답변] / [ASSISTANT · 섹션 구조 변경 제안]
  - [USER · 선택지 ① 채택] (직전 어시스턴트 질문의 보기 중 선택)
  - [USER] (자유 입력)

[ASSISTANT · 편집 제안] 메시지 안의 "[제시된 블록 수정 제안]" 항목 끝에는 사용자의 결정이 표시됩니다:
  - "→ 수락"  = 이미 문서에 반영됨 (현재 문서가 그 변경 이후 상태)
  - "→ 거절"  = 반영되지 않음
  - "→ 직접 지시(\"...\")" = 그 지시대로 후속 턴에서 재편집됨
  - "→ 대기"  = 결정 안 됨

[ASSISTANT · 섹션 구조 변경 제안] 메시지 안의 "[제시된 섹션 구조 변경]" 도 동일 규칙으로 결정이 표시됩니다.

[ASSISTANT · 사용자에게 질문] 메시지 안의 "[제시된 선택지]"는 직전에 사용자에게 보였던 보기 목록입니다.
직후 user가 "[USER · 선택지 ② 채택]"이면 그 번호의 보기가 골라진 것이고, 단순 "[USER]"이면 직접 입력입니다.

★ 중요 — 이 태그들은 입력 히스토리 해석용일 뿐입니다.
당신의 응답 본문에는 절대 "[ASSISTANT · ...]", "[USER · ...]", "[제시된 선택지]", "[제시된 블록 수정 제안]"
같은 태그/머리말을 포함하지 마세요. 사용자가 보는 화면에는 본문만 노출됩니다.
"""


@dataclass
class AgentSpec:
    name: str
    _system_template: str
    input_variables: list[str] = field(default_factory=list)
    model_kwargs: dict[str, Any] = field(default_factory=dict)
    output_schema: type | None = None

    def render_system(self, **vars: Any) -> str:
        expected = set(self.input_variables)
        provided = set(vars)
        missing = expected - provided
        extra = provided - expected
        if missing:
            raise ValueError(f"[{self.name}] missing prompt vars: {sorted(missing)}")
        if extra:
            raise ValueError(f"[{self.name}] unexpected prompt vars: {sorted(extra)}")
        rendered = _JINJA.from_string(self._system_template).render(**vars)
        # 모든 시스템 프롬프트 앞에 히스토리 포맷 해설을 자동 부착.
        # (LLM이 [ASSISTANT · ...] / [USER · 선택지 ① 채택] 같은 태그를 해석할 수 있게.)
        return HISTORY_FORMAT_NOTE + "\n" + rendered


def _resolve_schema(path: str) -> type:
    """`pkg.mod:Attr` → 클래스 객체."""
    mod_path, attr = path.split(":")
    return getattr(import_module(mod_path), attr)


@lru_cache(maxsize=None)
def load_agent_spec(name: str) -> AgentSpec:
    data = yaml.safe_load((_DIR / f"{name}.yaml").read_text(encoding="utf-8"))
    schema_path = data.get("output_schema")
    return AgentSpec(
        name=data["name"],
        _system_template=data["prompt"]["system"],
        input_variables=list(data.get("input_variables") or []),
        model_kwargs=dict(data.get("model") or {}),
        output_schema=_resolve_schema(schema_path) if schema_path else None,
    )
