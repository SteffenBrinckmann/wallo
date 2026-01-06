# AGENTS.md

This file provides guidance to LLM Agents when working with code in this repository.

## Project Overview

WALLO is a desktop writing assistant application built with PySide6 that integrates with Large Language Models (LLMs) to help users improve their writing. The application provides a rich text editor with formatting tools and customizable prompts that can be processed by various LLM services.

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

- **main.py**: Main application window (`Wallo` class) that handles UI, toolbar creation, and orchestrates LLM interactions
- **editor.py**: Custom `TextEdit` class extending QTextEdit with word wrap configuration
- **worker.py**: Background worker (`Worker` class) for LLM API calls and PDF processing to keep UI responsive
- **fixedStrings.py**: Configuration constants and default settings

### Key Architecture Patterns

1. **Threading Model**: Uses QThread for background LLM processing with signals/slots for communication
   1. Each call to backand with a work package creates a new thread. More advanced systems could be implemented in the future.
2. **Configuration System**: JSON-based configuration stored in `~/.wallo.json` with runtime defaults
3. **Prompt System**: Configurable prompts with different attachment modes (selection, PDF, inquiry)
4. **Service Architecture**: Multiple LLM service support through unified OpenAI-compatible interface
   1.  RAG and STT is only supported via OpenAI, currently

### Configuration Management

The application uses a JSON configuration file (`~/.wallo.json`) that includes:
- **prompts**: Array of prompt configurations with name, description, user-prompt, and attachment type
- **services**: Dictionary of LLM service configurations with API endpoints and models
- **promptFooter**: Default footer text appended to prompts
### Dependencies

- **PySide6**: Qt-based GUI framework
- **qtawesome**: Icon library for toolbar buttons
- **langchain**: All API calls are wrapped in langchain to get consistent API arguments
- **pdfplumber**: PDF text extraction

### Code Standards

- **Naming:** `camelCase` for variables, functions, methods, arguments, modules; `PascalCase` for classes; `UPPER_CASE` for constants.
- **Indentation:** 4 spaces (`indent-string='    '`), `indent-after-paren=4`.
- **Spacing** use two empty lines between each function
- **Imports:** `known-third-party=enchant`; no wildcard-with-`__all__` allowed.
- **Exception:** prefer broad Exceptions as they catch more issues
- **Spaces:** leave spaces inside a line untouched. The code is for human consumpt
- **Quotes:** use single quotes, when possible.


### Designed Code Limitations

- **General** Code should be as small as possible as short code, as short code is easy to understand and less prone to bugs. Hence, a broad exception is advantageous as it  catches all exceptions. Also, chopping code into submodules, can lead to more code and hence is not necessarily a great approach.
- **Security** storing plaintext API keys in `~/.wallo.json`, is allows changing manually the configuration. Since the code is open-source, all other solutions are only window-dressing: a hacker can read the obfuscation approach and counter it.
- **Unit tests** and **CI (Github)** does not make sense. End-2-End testing makes sense, but unit-tests do not. Testing if a blue button is still blue, makes no sense.
- **Standardize error output**. It makes more sense to fix errors than to make them pretty, more user focused.

### Job description

**Check for overcomplicated logic and redundant or inconsistent operations (e.g., adding and then subtracting the same value). Suggest simplifications.**
