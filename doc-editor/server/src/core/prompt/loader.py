from __future__ import annotations

from functools import lru_cache
from os import PathLike
from pathlib import Path

import yaml

from config import get_settings

from .model import PromptTemplate

settings = get_settings()


@lru_cache(maxsize=None)
def _load_template(base_path: Path, name: str) -> PromptTemplate:
    path = base_path / f"{name}.yaml"
    if not path.is_file():
        raise FileNotFoundError(f"Prompt template not found: {path}")
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return PromptTemplate.model_validate(data)

class PromptTemplateLoader:
    def __init__(self, base_path: str | PathLike[str] | None = None):
        self.base_path = Path(base_path or settings.prompt_base_path)

    def load(self, name: str) -> PromptTemplate:
        return _load_template(self.base_path, name)
    
@lru_cache
def get_prompt_loader() -> PromptTemplateLoader:
    return PromptTemplateLoader()
