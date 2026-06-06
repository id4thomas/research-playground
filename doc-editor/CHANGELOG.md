# Changelog

## v0.1.2 (2026.06.05)
[History (ChatMessage) Refactor]
- Introduce “InteractionChatMessage” that contains user interaction information
    - status: user interaction status (pending/accepted/…)
- Add BlockAction (block edit), OutlineAction (section edit) types to better represent edits
- Add ClarifyChatMessage to handle option options & response

[Document Representation Refactor]
- Introduct “text”, “table”, “equation” block types
- Add “format” attribute (html/markdown/tex/..)

[Document Block, Outline Edit Refactor]
- Make BlockEdit, OutlineEdit in core.data.edit
    - unify specification in agent operation & frontend wire (chat history)
- BlockEditGenerate operation uses _to_block_edit to convert LLM output to BlockEdit instance

[Prompts]
- Add output json specification instructions to each prompts
- Add maxItems constraint to context gather prompt

## v0.1.1 (2026.06.03)
**[Agent Implementation]**
- **Clean up hierarchy:** Agent > Node > Operation
- **History Formatter:** Common utility to format message history as context
- **Reduce SubGraph State Dependency:** wrap subgraph with function before adding to upper graph as node, the function handles state conversion
- **Structured Output:** Pass json schema instead of Pydantic definition to  ChatOpenAI with_structured_output
    - Make schema overridable in runtime

**[LLM Operation]**
- **Prompt Management:** Add Prompt Loader, Prompt Template Model (core.prompt)
- **BaseLLMOperation:** Wrap common prompt loading, llm invoke

**[Deployment]**
- add Dockerfile for server, frontend
- add docker-compose file for deployment