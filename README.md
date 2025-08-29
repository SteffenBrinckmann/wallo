![Logo](images/wallo.png "Logo")

# WALLO - Writing Assistant leveraging Large Language mOdels

Often you have to write a text and forget all the helpful prompts that you used in the past. This tool helps to reduce the copy-paste from your local prompt-library and into the LLM-tools.

This program has been heavily written by Claude; at a certain point I let it just change the code.

![Screenshot](images/screenshot.png "Screenshot")

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

Prompts and services are saved in .wallo.json file in your home folder.

## Development
### Things I might/might not add

- Word wrap does not work with long copy-paste content
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
