"""Operations — stateless, re-usable units invoked by Nodes."""
from agent.operations.answer_generate import (
    AnswerGenerateOperation,
    AnswerGenerateOutput,
)
from agent.operations.clarify_generate import (
    ClarifyGenerateOperation,
    ClarifyGenerateOutput,
)
from agent.operations.context_collect import (
    ContextCollectOperation,
    ContextCollectOutput,
)
from agent.operations.block_edit_generate import (
    BlockEditGenerateOperation,
    BlockEditGenerateOutput,
    render_document,
)
from agent.operations.intent_classify import (
    INTENTS,
    IntentClassifyOperation,
    IntentClassifyOutput,
)
from agent.operations.outline_edit_generate import (
    OutlineEditGenerateOperation,
    OutlineEditGenerateOutput,
)
from agent.operations.strip_codes import StripCodesOperation

__all__ = [
    "AnswerGenerateOperation",
    "AnswerGenerateOutput",
    "ClarifyGenerateOperation",
    "ClarifyGenerateOutput",
    "ContextCollectOperation",
    "ContextCollectOutput",
    "BlockEditGenerateOperation",
    "BlockEditGenerateOutput",
    "render_document",
    "INTENTS",
    "IntentClassifyOperation",
    "IntentClassifyOutput",
    "OutlineEditGenerateOperation",
    "OutlineEditGenerateOutput",
    "StripCodesOperation",
]
