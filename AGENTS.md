# AGENTS.md

This file provides guidance to LLM Agents when working with code in this repository.

## Project Overview

WALLO is a desktop writing assistant application built with PySide6 that integrates with Large Language Models (LLMs) to help users improve their writing.
- Document structure: A document is a sequence of exchanges. Each exchange contains a task history and the LLM's reply.
- User workflow: Users enter or edit the task history, request the LLM to perform a task, and receive an editable reply. Both the task history and the
  LLM reply can always be modified. While the LLM is running, users may edit other exchanges.
- Tools and shortcuts:
  - Nine tools (btns variable in __init__ of exchange.py) are arranged in a numeric-pad layout to support the user:
    - First row: task-history tools
    - Second row: LLM tools
    - Third row: miscellaneous tools
    - Tool mapping
      - 7: self.hide1
      - 8: self.audio1
      - 9: self.move2to1
      - 4: self.chatExchange
      - 5: self.toggleRag
      - 6: self.attachFile
      - 1: self.splitParagraphs
      - 2: self.addExchangeNext
      - 3: self.showStatus
  - A drop-down menu provides access to all LLM prompts. These prompts are customizable and can be processed by various LLM services.
  - Keyboard shortcuts: Ctrl+1 … Ctrl+9 trigger LLM prompts; Alt+1 … Alt+9
    activate the corresponding tools.

## Development Commands

### Installation and Setup
```bash
python -m venv .venv
pip install -r requirements.txt
```

### Running the Application
```bash
. .venv/bin/activate
python -m wallo.main
```

### Development Tools
```bash
# Type checking
mypy wallo/

# Linting
pylint wallo/
```

## Architecture

### Core Components
Package wallo/
- **main.py**: Main application window (`Wallo` class) that handles UI, toolbar creation, and creates the list of exchanges
- **exchange.py**: each exchange is a UI element that has two editors and buttons for the tools
- **editor.py**: Custom `TextEdit` class extending QTextEdit with word wrap configuration
- **worker.py**: Background worker (`Worker` class) for LLM API calls and PDF processing to keep UI responsive
- **llmProcessor.py**: houses all logic regarding the LLM usage
- **agents.py**: all agents are defined here as well as their functions

### Key Architecture Patterns

1. **Threading Model**: Uses QThread for background LLM processing with signals/slots for communication
   1. A new QThread is created for each sequential call to backend. More advanced systems could be implemented in the future.
2. **Configuration System**: JSON-based configuration stored in `~/.wallo.json` with runtime defaults
3. **Prompt System**: Configurable prompts with an inquiry mode (boolean to signal if it is on or off) (see wallo/configTabPrompts.py)
4. **Service Architecture**: Multiple LLM service support through unified langchain API
   1.  RAG, STT can only use OpenAI as the code only uses langchain-OpenAI, currently. The user cannot change this. (see wallo/llmProcessor.py)
   2.  TTS is hardwired to use OpenAI TTS. The user cannot change this. (see wallo/worker.py)


### Configuration Management

The application uses a JSON configuration file (`~/.wallo.json`) that includes (see wallo/conigSchema.json):
- **prompts**: Array of prompt configurations with name, description, user-prompt, and attachment type
- **services**: Dictionary of LLM service configurations with API endpoints and models

### Dependencies

- **PySide6**: Qt-based GUI framework
- **langchain**: All API calls are wrapped in langchain to get consistent API arguments

### Code Standards

- **Naming:** `camelCase` for variables, functions, methods, arguments; `PascalCase` for classes; `UPPER_CASE` for constants.
  - do not rename files
- **Indentation:** 4 spaces (`indent-string='    '`), `indent-after-paren=4`.
- **Spacing** use two empty lines between each function
- **Imports:** no wildcard-with-`__all__` allowed.
- **Exception:** Prefer no exceptions; if needed, catch broad exceptions only at UI/worker boundaries.
- **Spaces:** Don’t run auto-formatters; preserve whitespaces inside a code line.
- **Quotes:** use single quotes, when possible.
- **Reduce get-usage** for dictionaries unless a default value is given. Prefer to use index-notation [] for readability.
- **Refactoring** Prefer small patches; avoid refactors unless requested.

### Designed Code Limitations

- **General** Code should be as small as possible as short code, as short code is easy to understand and less prone to bugs. Hence, a broad exception is advantageous as it  catches all exceptions. Also, chopping code into submodules, can lead to more code and hence is not necessarily a great approach.
- **Security** storing plaintext API keys in `~/.wallo.json`, allows changing the values manually. Since the code is open-source, all other solutions are only window-dressing: a hacker can read the obfuscation approach and counter it.
- **Unit tests** and **CI (Github)** We don’t add unit tests; CI is only for lint/type/codespell.
- Do not implement **standardized error output**; keep error handling minimal.
- Do not refactor code into a separate function that function is called only a single time.
- Do not remove comments when changing code. Preserve it.
- **Use Langchain as much as possible**. It simplifies the code to support multiple services.
- **Config migration**: This code is in development mode. Do not worry about changing the config precedence.

### Job description

**Check for overcomplicated logic and redundant or inconsistent operations (e.g., adding and then subtracting the same value). Suggest simplifications.**
