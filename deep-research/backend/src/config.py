from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Literal

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class LLMClientConfig(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    base_url: str = "http://localhost:901/v1"
    api_key: str = "sk-123"

class TracingConfig(BaseSettings):
    """LLM/Agent tracing (datadog)"""

    enabled: bool = False
    app: str = "deep-research-v2"
    site: str | None = None
    api_key: str | None = None



class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", env_nested_delimiter="__", extra="ignore"
    )
    # logging: LoggingSettings = Field(default_factory=LoggingSettings)
    
    llm: LLMClientConfig = Field(default_factory=LLMClientConfig)
    tracing: TracingConfig = Field(default_factory=TracingConfig)


@lru_cache
def get_settings():
    return Settings()
