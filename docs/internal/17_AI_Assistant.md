# AI Assistant Integration

BioPro features an integrated AI Assistant (`biopro.ui.ai.service.AIService`) designed to provide contextual documentation retrieval and operational guidance within the application.

---

## Core Functionality

- **Context-Aware Retrieval**: The assistant utilizes a context panel (`biopro.ui.ai.context_panel.ContextPanel`) to allow users to select which internal documentation or plugin-specific manuals are included in the prompt context.
- **Asynchronous Execution**: Queries are executed via the `StreamingAIThread`, ensuring the primary UI thread remains responsive during LLM generation.
- **Session Isolation**: Chat history is managed by the `AIService` and can be explicitly cleared (`clear_history()`). Sessions do not persist across project closures.

---

## Managing Context

To optimize prompt fidelity and remain within token limits, BioPro relies on explicit context selection.

### Core Documentation
Users can select specific core manuals to include in the context window.

### Plugin Documentation
When an analysis module is active, the Context Panel detects and allows the inclusion of plugin-specific documentation.

---

## Technical Specifications

- **Execution Threading**: The `StreamingAIThread` inherits from `QThread` and emits `chunk_received(str)`, `finished(dict)`, and `error(str)` signals to stream responses to the UI asynchronously.
- **Service Orchestration**: The `AIService` coordinates the underlying `AIAssistant` SDK integration, managing the chat Markdown state and the selected context file references.
