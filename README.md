![Logo](images/wallo.png "Logo")

# WALLO - Writing Assistant based on Large Language mOdels

Often you have to write a text and forget all the helpful prompts that you used in the past. This tool helps to reduce the copy-paste from your local prompt-library and into the LLM-tools.

WARNING: This is a side project as I have more than enough things to maintain. If it does not work for you, fix it yourself and create a PR.

This program has been heavily written by Claude; at a certain point I let it just change the code.


## Installation and usage

Installation:
```bash
  git clone git@github.com:SteffenBrinckmann/wallo.git
  cd wallo/
  python -m venv .venv
  pip install -r requirements.txt
```
Usage:
```bash
  . .venv/bin/activate
  python -m wallo.main
```

## Configuration

Prompts and services are saved in .wallo.json file in your home folder.


## Things I might/might not add

- Word wrap does not work with long copy-paste content
- pyInstaller to easily install on windows
- pip
