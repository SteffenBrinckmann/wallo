# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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
- **busyDialog.py**: Progress dialog (`BusyDialog`) for showing work status
- **fixedStrings.py**: Configuration constants and default settings

### Key Architecture Patterns

1. **Threading Model**: Uses QThread for background LLM processing with signals/slots for communication
2. **Configuration System**: JSON-based configuration stored in `~/.wallo.json` with runtime defaults
3. **Prompt System**: Configurable prompts with different attachment modes (selection, PDF, inquiry)
4. **Service Architecture**: Multiple LLM service support through unified OpenAI-compatible interface

### Configuration Management

The application uses a JSON configuration file (`~/.wallo.json`) that includes:
- **prompts**: Array of prompt configurations with name, description, user-prompt, and attachment type
- **services**: Dictionary of LLM service configurations with API endpoints and models
- **promptFooter**: Default footer text appended to prompts

### Prompt Attachment Types

- `selection`: Works with selected text in the editor
- `pdf`: Processes uploaded PDF files using pdfplumber
- `inquiry`: Prompts user for input with dynamic text replacement

### Dependencies

- **PySide6**: Qt-based GUI framework
- **qtawesome**: Icon library for toolbar buttons
- **openai**: OpenAI API client (used for all LLM services)
- **pypandoc**: Document conversion (currently commented out)
- **pdfplumber**: PDF text extraction

### Type Checking Configuration

The project uses mypy with strict settings:
- `disallow_untyped_defs = true`
- `check_untyped_defs = true`
- `warn_unused_ignores = true`
- `ignore_missing_imports = true`