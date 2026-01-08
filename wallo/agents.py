""" Define agents that can be used by application """
import json
from typing import Any
from urllib.parse import quote_plus
from urllib.request import Request, urlopen
from langchain_core.tools import tool

USE_AGENTS = True

def _httpJson(url: str, method: str = 'GET', headers: dict[str, str]|None = None,
              data: dict[str, Any]|None = None, timeout: float = 20.0) -> Any:
    """Minimal JSON HTTP helper (urllib-based)."""
    body: bytes|None = None
    requestHeaders = headers or {}
    if data is not None:
        body = json.dumps(data).encode('utf-8')
        requestHeaders = {**requestHeaders, 'Content-Type': 'application/json'}
    request = Request(url, data=body, headers=requestHeaders, method=method)
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode('utf-8'))


def _formatResults(query: str, provider: str, results: list[dict[str, str]]) -> str:
    if not results:
        return f'No results found for: {query}'
    lines = [f'Websearch results ({provider})', f'- Query: {query}']
    for i, item in enumerate(results[:5], start=1):
        title = item.get('title', '').strip()
        url = item.get('url', '').strip()
        snippet = item.get('snippet', '').strip()
        if title:
            lines.append(f'- {i}. {title} | {url}')
        else:
            lines.append(f'- {i}. {url}')
        if snippet:
            lines.append(f'  {snippet}')
    return '\n'.join(lines)


@tool
def websearch(query: str) -> str:
    """Web search tool used by agent-mode.
    - uses DuckDuckGo Instant Answer API

    Returns a compact, text-only result list for LLM consumption.
    """
    query = (query or '').strip()
    if not query:
        return 'No query provided.'
    try:
        url = 'https://api.duckduckgo.com/?q='+quote_plus(query)+'&format=json&no_html=1&skip_disambig=1'
        data = _httpJson(url)
        results: list[dict[str, str]] = []
        abstractText = (data.get('AbstractText') or '').strip()
        abstractUrl = (data.get('AbstractURL') or '').strip()
        if abstractText and abstractUrl:
            results.append({'title': 'Instant Answer', 'url': abstractUrl, 'snippet': abstractText})

        def collect(topicList: list[Any]) -> None:
            for topic in topicList:
                if isinstance(topic, dict) and 'Topics' in topic:
                    collect(topic['Topics'])
                    continue
                if not isinstance(topic, dict):
                    continue
                firstUrl = (topic.get('FirstURL') or '').strip()
                text = (topic.get('Text') or '').strip()
                if firstUrl and text:
                    results.append({'title': text.split(' - ', 1)[0], 'url': firstUrl, 'snippet': text})

        collect(data.get('RelatedTopics', []) or [])
        return _formatResults(query, 'duckduckgo', results)
    except Exception as e:
        return f'Websearch failed (duckduckgo): {str(e)}'


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
        "Tool available: websearch(query: str) -> str (online; uses Tavily if TAVILY_API_KEY is set).\n"
        'Select exactly one agent persona per user request:\n'
        '- Use NewUserHelper for product usage and onboarding questions.\n'
        '- Use AddonHelper for addon/plugin development questions.\n'
        "Start your answer with 'Active agent: <name>'.\n"
    )
    return coordinator + '\n' + newUserHelper + '\n' + addonHelper
