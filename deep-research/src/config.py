from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Literal

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMClientConfig(BaseSettings):
    base_url: str = "http://localhost:901/v1"
    api_key: str = "sk-123"

class TracingConfig(BaseSettings):
    """LLM/Agent Tracing (mlflow)"""
    uri: str = "http://localhost:7000"
    experiment: str = "2603-2-deepsearch"

class LoggingSettings(BaseModel):
    log_level: Literal["debug", "info", "warning", "error", "critical"] = Field("info", description="Log level")
    format: Literal["console", "json"] = Field("console", description="Log format")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", env_nested_delimiter="__", extra="ignore"
    )
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    
    llm: LLMClientConfig = Field(default_factory=LLMClientConfig)
    tracing: TracingConfig = Field(default_factory=TracingConfig)

# def load_feature_prompts() -> Dict[str, PromptInfo]:
#     """Load feature prompt configurations from YAML file."""
#     index_path = Path(__file__).parent / "index.yaml"

#     with open(index_path, "r") as f:
#         prompt_index = yaml.safe_load(f)
    


# Load feature prompts at module level
# FEATURE_PROMPTS: dict[str, PromptInfo] = load_feature_prompts()


@lru_cache
def get_settings():
    return Settings()


# @lru_cache
# def get_prompt_info(feature: str) -> PromptInfo:
#     return FEATURE_PROMPTS[feature]
