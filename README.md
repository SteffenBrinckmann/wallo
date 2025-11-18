![Logo](images/wallo.png "Logo")

# WALLO - Writing Assistant leveraging Large Language mOdels

An intelligent writing partner that helps you craft clear, compelling manuscripts with ease while enhancing creativity.

## 1. Seamless Integration
Many writers rely on traditional text editors (e.g., Microsoft Word) while simultaneously using a Large Language Model (LLM) such as ChatGPT in a separate browser window—constantly copying and pasting between the two. This process is inefficient and disrupts creative flow. Programmers no longer work this way; their LLMs are fully integrated into their development environments.

**WALLO** brings the same seamless integration to writing by allowing users to directly "Make the text sound more professional.”, “Expand these bullet points into a cohesive paragraph.”, “Condense or expand this section to 200 words.” or “Summarize this PDF.”

## 2. Enhanced Ideation
Writers often turn to LLMs for brainstorming. While the process can be informative, they are often inconsistent. Productive ideas can get lost in long exchanges.
With **WALLO**, ideation and refinement happen in one software. You can highlight key insights within your conversation and filter out garbage.

## 3. Workflow
LLMs will change how 99% of users operate computers. **WALLo** allows users to test different workflows, user-interfaces-experiences-things. Hence, **WALLO** and its design will **evolve**, as certain things work, goals change, ... If you have ideas, open an issue and lets get into the discussion.

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
- reduce does not fully work, debug

### Things I do not want to add
- pyInstaller to easily install on windows (only makes sense if finished program. Not the goal of this **Evolutionary Software**)
- Ensure long-running file operations and LLM calls surface progress and support cancellation. (Not the goal of this **Evolutionary Software**)
- Add timeout and retry/backoff logic for LLM API calls. (Not the goal of this **Evolutionary Software**)

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
