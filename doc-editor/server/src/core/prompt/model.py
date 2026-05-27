from abc import ABC, abstractmethod
from typing import Any, Literal

from jinja2 import Environment, StrictUndefined
from pydantic import BaseModel, Field


class TemplateFormatter(ABC):
    """Formatting strategy interface."""

    @abstractmethod
    def render(self, text: str, variables: dict[str, Any]) -> str:
        """Render `text` by substituting `variables` into it."""
        ...


class FStringTemplateFormatter(TemplateFormatter):
    """Renders templates using Python str.format() (f-string style)."""

    def render(self, text: str, variables: dict[str, Any]) -> str:
        try:
            return text.format(**variables)
        except KeyError as e:
            missing = e.args[0]
            raise ValueError(f"Missing variable '{missing}' for f-string item") from e
        except Exception as e:
            raise ValueError(f"Error formatting f-string item: {e}") from e


class JinjaTemplateFormatter(TemplateFormatter):
    """Renders templates using the Jinja2 engine."""

    def __init__(self) -> None:
        # StrictUndefined makes missing variables raise instead of rendering empty.
        self._env = Environment(undefined=StrictUndefined, autoescape=False)

    def render(self, text: str, variables: dict[str, Any]) -> str:
        try:
            template = self._env.from_string(text)
            return template.render(variables)
        except Exception as e:
            raise ValueError(f"Error rendering Jinja2 item: {e}") from e


# Map format name -> a single reusable formatter instance.
# Formatters are stateless across calls, so one instance each is enough.
FORMATTERS: dict[str, TemplateFormatter] = {
    "f-string": FStringTemplateFormatter(),
    "jinja2": JinjaTemplateFormatter(),
}


class MessageTemplate(BaseModel):
    """OpenAI Chat Completion message-like class."""

    role: str = Field("user", description="Message role")
    content: str = Field(..., description="Message content")
    input_variables: list[str] | None = Field(
        default=None,
        description="List of input variables used in the message",
    )


class GenerationParameters(BaseModel):
    """Model info and generation parameters."""

    provider: str = Field(
        ...,
        description="Model provider (e.g. openai / anthropic / gemini)",
    )
    name: str = Field(..., description="Model name")
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Extra generation parameters",
    )


class OutputSchema(BaseModel):
    """Structured output schema."""

    type: Literal["text", "json_object", "json_schema"] = Field(
        "text",
        description="Output type",
    )
    json_schema: dict[str, Any] | None = Field(
        None,
        description="Output JSON schema",
    )


class PromptTemplate(BaseModel):
    """A reusable prompt definition: messages, output schema, and model parameters."""

    template_format: Literal["jinja2", "f-string"] = Field(
        "jinja2", description="Template format"
    )
    messages: list[MessageTemplate] = Field(
        default_factory=list, description="List of message templates"
    )
    output_schema: OutputSchema | None = Field(None, description="Output schema")
    parameters: GenerationParameters | None = Field(
        None, description="Model and generation parameters"
    )

    def fill_template(self, contents: dict[str, str]) -> list[MessageTemplate]:
        """Fill each message's content with the given variables.

        Args:
            contents: Mapping of variable name -> value.

        Returns:
            New message templates with rendered content (originals untouched).
        """
        formatter = FORMATTERS[self.template_format]

        filled = []
        for message_template in self.messages:
            message = message_template.model_copy()
            message.content = formatter.render(
                text=message.content, variables=contents
            )
            filled.append(message)

        return filled