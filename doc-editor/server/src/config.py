from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMClientConfig(BaseSettings):
    base_url: str = "http://localhost:901/v1"
    api_key: str = "EMPTY"
    model: str = "Qwen3.6-35B-A3B"


class TracingConfig(BaseSettings):
    """LLM/Agent tracing (mlflow)"""
    enabled: bool = True
    uri: str = "http://localhost:7000"
    experiment: str = "2605-doc-editor"


class LoggingSettings(BaseModel):
    log_level: Literal["debug", "info", "warning", "error", "critical"] = Field(
        "info", description="Log level"
    )
    format: Literal["console", "json"] = Field("console", description="Log format")


class AgentConfig(BaseModel):
    # 단일 패스 그래프라 별도 반복 설정은 없음. 자리만 유지.
    pass


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
    )
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    llm: LLMClientConfig = Field(default_factory=LLMClientConfig)
    tracing: TracingConfig = Field(default_factory=TracingConfig)
    agent: AgentConfig = Field(default_factory=AgentConfig)


@lru_cache
def get_settings() -> Settings:
    return Settings()
