![Logo](images/wallo.png "Logo")

# WALLO - Writing Assistant leveraging Large Language mOdels

An intelligent writing partner that helps you craft clear, compelling manuscripts and narratives with ease while enhancing creativity.

## 1. Seamless Integration
Many writers rely on traditional text editors (e.g., Microsoft Word) while simultaneously using a Large Language Model (LLM) such as ChatGPT in a separate browser window—constantly copying and pasting between the two. This process is inefficient and disrupts creative flow. Programmers no longer work this way; their LLMs are fully integrated into their development environments.

**WALLO** brings the same seamless integration to writing, embedding advanced language assistance directly into your editor.

Example use cases:
- “Make the text sound more professional.”
- “Expand these bullet points into a cohesive paragraph.”
- “Condense or expand this section to 200 words.”
- “Summarize this PDF.”

## 2. Enhanced Ideation
Writers often turn to LLMs for brainstorming and exploration—asking questions like “What cultural shifts accompanied the invention of book printing?” While responses can be informative, they are often inconsistent in focus or length. Productive ideas can get lost in long exchanges.

With **WALLO**, ideation and refinement happen in one unified workspace. You can highlight key insights within your conversation, while WALLO filters out tangents and redundancies—preserving what matters most.

## 3. Workflow
Although most computer users are proficient at rapid copy-and-paste operations and switching between applications, these workflows remain relatively inefficient. Professional gamers routinely execute hundreds of actions per minute, typically using the mouse with their right hand while their left hand performs keyboard shortcuts.

**WALLO** delegates mouse interactions to highlighting and scrolling, while the left hand relies on configurable shortcuts to manage text: select segments, invoke the LLM (Ctrl+1), or reduce text length (Ctrl+R).

---
![Screenshot](images/screenshot.png "Screenshot")

The writing of this program code and documentation are supported by LLMs (Antropic's Claude, openAI GPT-5-mini).


## Installation and usage
### Using pypi
```bash
  python -m venv .venv
  . .venv/bin/activate
  pip install wallo
```

### Github
```bash
  git clone git@github.com:SteffenBrinckmann/wallo.git
  cd wallo/
  python -m venv .venv
  . .venv/bin/activate
  pip install -r requirements.txt
```

### Usage
Usage:
```bash
  . .venv/bin/activate
  python -m wallo.main
```


## Configuration

Prompts, services and the other configuration settings are saved in .wallo.json file in your home folder.

## Development
### Things I might/might not add

- Spell checking
- pyInstaller to easily install on windows

### Upload to pypi
How to upload to pypi

1. Update version number in pyproject.toml
2. Execute commands
    ``` bash
      mypy wallo/
      pylint wallo/
      python3 -m build
      python3 -m twine upload dist/*
    ```
