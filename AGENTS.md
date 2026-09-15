# AGENTS.md

## Project Overview

WALLO is a PySide6 desktop writing assistant integrated with LLMs. A document is a sequence of exchanges, each containing editable task history and LLM reply. Users may edit other exchanges while an LLM runs.

Tools use the numeric-pad layout defined by `btns` in `exchange.py`: 7 hide, 8 audio, 9 move reply to history, 4 chat, 5 toggle RAG, 6 attach file, 1 split paragraphs, 2 add exchange, 3 show status. Ctrl+1–9 trigger prompts; Alt+1–9 activate tools.

## Development Commands

```bash
python -m venv .venv
pip install .[dev]
. .venv/bin/activate
python -m wallo.main
mypy wallo/
pylint wallo/
```

## Architecture

- `main.py`: main application window and exchange list.
- `exchange.py`: exchange UI element with editors and tools.
- `editor.py`: custom `TextEdit`.
- `worker.py`: background worker for LangChain/OpenAI, STT/TTS, and RAG ingestion.
- `acpWorker.py`: ACP helper with a shared ACP session, shared temporary workspace, and serialized prompt execution.
- `llmProcessor.py`: LLM-use logic.
- `agents.py`: agents and their functions.

LangChain/OpenAI uses `QThread` signals/slots. ACP runs on a dedicated asyncio-loop thread and serializes prompts to preserve shared-session context. Configuration is JSON in `~/.wallo.json`; prompts and services follow `configSchema.json`. `CHAT_TRANSPORT` in `main.py` selects ACP or the fallback worker/LangChain path. RAG/STT and TTS use OpenAI; ACP shares one session ID and temporary directory per run.

## Project-Specific Rules

- Do not rename files.
- Preserve whitespace inside a code line and do not run auto-formatters.
- Prefer no exceptions; catch broad exceptions only at UI/worker boundaries.
- Reduce dictionary `get` use unless a default is needed; prefer `[]` for readability.
- Do not add tests: WALLO deliberately treats prototype GUI behavior as not needing automated tests. CI is lint/type/codespell only.
- Use LangChain where possible to support multiple services.
- The project is in configuration-development mode; do not worry about config precedence migrations.
- Plaintext API keys in `~/.wallo.json` are intentional. Do not add standardized error output.
- `README.md` may intentionally include long shell-output dumps.
- Open issues are tracked only in `README.md`; do not add repository issue-tracker links.
