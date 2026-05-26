"""Tracing utilities.

`settings.tracing.enabled=False`일 때 mlflow를 호출하지 않도록 감싸는 헬퍼.
서비스 코드는 `with start_span("name") as span:` 형태로 사용하면 되고,
disabled면 no-op context manager가 반환된다.
"""
from contextlib import contextmanager
from typing import Any

import mlflow

from config import get_settings

_settings = get_settings()


class _NoopSpan:
    """mlflow span 인터페이스의 일부를 흉내내는 no-op."""

    def set_inputs(self, *_a: Any, **_kw: Any) -> None:  # noqa: D401
        pass

    def set_outputs(self, *_a: Any, **_kw: Any) -> None:
        pass

    def set_attribute(self, *_a: Any, **_kw: Any) -> None:
        pass


@contextmanager
def start_span(name: str):
    """tracing 활성 시 mlflow span, 아니면 no-op."""
    if _settings.tracing.enabled:
        with mlflow.start_span(name=name) as span:
            yield span
    else:
        yield _NoopSpan()


def is_enabled() -> bool:
    return _settings.tracing.enabled
