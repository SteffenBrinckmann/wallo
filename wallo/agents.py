""" Define agents that can be used by application """
from typing import Any
from langchain_core.tools import tool

USE_AGENTS = True

@tool
def websearch(query: str) -> str:
    """Dummy web search tool.

    For now this is a placeholder so we can wire up function calling.
    """
    query = (query or '').strip()
    if not query:
        return 'No query provided.'
    return (
        'Dummy websearch results (offline)\n'
        f'- Query: {query}\n'
        '- Result 1: https://example.com/docs\n'
        '- Result 2: https://example.com/tutorial\n'
    )


def getAgentTools() -> list[Any]:
    """Tools available in agent-mode.
    Returns:
        List of tools.
    """
    return [websearch]


def getAgentCoordinatorPrompt() -> str:
    """Agent prompts
    Returns:
        Agent coordinator prompt
    """
    newUserHelper = (
        'Agent: NewUserHelper\n'
        '- Goal: help brand-new users succeed quickly.\n'
        '- Behavior: ask at most 2 clarifying questions if needed, then give short step-by-step instructions.\n'
        '- If unsure: suggest the next best action and how to verify it.\n'
    )
    addonHelper = (
        'Agent: AddonHelper\n'
        '- Goal: help users write addons/extensions for the main product.\n'
        "- Behavior: propose a minimal design first (API surface, file list), then produce code in small chunks.\n"
        '- Always include: assumptions, integration steps, and a quick test/run command.\n'
    )
    coordinator = (
        'You are operating in WALLO agent-mode.\n'
        'You have access to tools and may call them when needed.\n'
        "Tool available: websearch(query: str) -> str (dummy, offline).\n"
        'Select exactly one agent persona per user request:\n'
        '- Use NewUserHelper for product usage and onboarding questions.\n'
        '- Use AddonHelper for addon/plugin development questions.\n'
        "Start your answer with 'Active agent: <name>'.\n"
    )
    return coordinator + '\n' + newUserHelper + '\n' + addonHelper
