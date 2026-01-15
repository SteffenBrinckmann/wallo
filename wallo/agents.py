""" Define agents that can be used by application """
import json
import sqlite3
from typing import Any
from urllib.parse import quote_plus
from urllib.request import Request, urlopen
from langchain_core.tools import tool

class Agents:
    """Class to house agent coordinator and tools."""
    def __init__(self) -> None:
        self.useAgents                             = False
        self.usePastaEln                           = ''
        self.websearchTool = tool('websearch')(self._websearch)
        self.sqliteDescribeTool = tool('sqliteDescribe')(self._sqliteDescribe)
        self.sqliteQueryTool = tool('sqliteQuery')(self._sqliteQuery)


    @classmethod
    def _httpJson(cls, url: str, method: str = 'GET', headers: dict[str, str]|None = None,
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


    @classmethod
    def _formatResults(cls, query: str, provider: str, results: list[dict[str, str]]) -> str:
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


    def _websearch(self, query: str) -> str:
        """Web search tool used by agent-mode.
        - uses DuckDuckGo Instant Answer API.

        Returns a compact, text-only result list for LLM consumption.
        """
        query = (query or '').strip()
        if not query:
            return 'No query provided.'
        try:
            url = 'https://api.duckduckgo.com/?q=' + quote_plus(query) + '&format=json&no_html=1&skip_disambig=1'
            data = self._httpJson(url)
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
            return self._formatResults(query, 'duckduckgo', results)
        except Exception as e:
            return f'Websearch failed (duckduckgo): {str(e)}'


    def _sqliteDescribe(self) -> str:
        """Return the sqlite database purpose and schema."""
        try:
            with sqlite3.connect(self.usePastaEln, timeout=5.0) as conn:
                cmd = "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
                tables = [row[0] for row in conn.execute(cmd).fetchall()]
                schema: dict[str, list[dict[str, Any]]] = {}
                for table in tables:
                    cols = conn.execute(f"PRAGMA table_info('{table}')").fetchall()
                    schema[table] = [{'name': c[1], 'type': c[2], 'notnull': c[3], 'pk': c[5]} for c in cols]
            return json.dumps({'purpose': self.getSqlPurpose(), 'tables': schema}, ensure_ascii=False)
        except Exception as e:
            return f'sqliteDescribe failed: {str(e)}'


    def _sqliteQuery(self, query: str, params: dict[str, Any]|None = None, limit: int = 50) -> str:
        """Run a read-only SELECT query against the configured sqlite database."""
        query = (query or '').strip()
        if not query:
            return 'No query provided.'
        if not query.lower().startswith('select'):
            return 'Only SELECT queries are allowed.'
        limit = max(1, min(int(limit), 200))
        try:
            with sqlite3.connect(self.usePastaEln, timeout=5.0) as conn:
                conn.row_factory = sqlite3.Row
                cur = conn.execute(query, params or {})
                rows = cur.fetchmany(limit)
                result = [dict(r) for r in rows]
            return json.dumps(result, ensure_ascii=False)
        except Exception as e:
            return f'sqliteQuery failed: {str(e)}'


    def getAgentTools(self) -> None|list[Any]:
        """Tools available in agent-mode.
        Returns:
            List of tools.
        """
        if not self.useAgents:
            return None
        if self.usePastaEln:
            return [self.websearchTool, self.sqliteDescribeTool, self.sqliteQueryTool]
        return [self.websearchTool]


    def getAgentCoordinatorPrompt(self) -> str:
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
            '- Behavior: propose a minimal design first (API surface, file list), then produce code in small chunks.\n'
            '- Always include: assumptions, integration steps, and a quick test/run command.\n'
        )
        coordinator = (
            'You are operating in WALLO agent-mode.\n'
            'You have access to tools and may call them when needed.\n'
            'Tools available:\n'
            '- websearch(query: str) -> str (online; uses DuckDuckGo Instant Answer API).\n'
        )
        if self.usePastaEln:
            coordinator += (
            '- sqliteDescribe() -> str. (To describe the sql database that PASTA-ELN uses to store scientific,'
            ' materials science data)\n- sqliteQuery(query: str, params: dict|None, limit: int) -> str (read-only.'
            ' Database that stores the data for PASTA-ELN).\n'
            )
        coordinator += (
            'If the user asks about the sqlite database, call sqliteDescribe() first.\n'
            'Select exactly one agent persona per user request:\n'
            '- Use NewUserHelper for product usage and onboarding questions.\n'
            '- Use AddonHelper for addon/plugin development questions.\n'
            "Start your answer with 'Active agent: <name>'.\n"
        )
        return coordinator + '\n' + newUserHelper + '\n' + addonHelper


    def getSqlPurpose(self) -> str:
        """ Return string about the purpose and layout of the PASTA-ELN database."""
        return """
            PASTA‑ELN instance database for a single user’s group of projects. WALLO uses this SQLite database strictly as read‑only context to answer
            questions about the ELN content; it must never write to or modify the file. The database is the canonical storage owned and updated by
            PASTA‑ELN (content changes roughly weekly), and multiple WALLO instances may open it concurrently in read-only mode.

            Core data model: each ELN entity (“item”) is stored in main (one row per item). main.id is the stable identifier. main.name is a user-given
            label. main.type is the item/document type and should normally match docTypes.docType; a value of '-' indicates an undefined/unknown type.
            main.content and main.comment are free-text Markdown that can be searched for topics/keywords. Items are organized into a hierarchical
            project structure through branches entries; branches.path is the human-readable canonical location to report (e.g., project/task/subtask
            path). Visibility is controlled by the gui flags (e.g., TTT means all hierarchy levels visible); if any level contains F (false), the item
            should be treated as invisible/hidden in user-facing answers.

            Type system and metadata: the available item/document types are defined in docTypes (optionally including title/icon/shortcut/view metadata).
            Per-type schemas and expected fields are described by docTypeSchema. Items can carry additional extensible metadata in properties as key/
            value pairs with optional units; shared explanations for keys live in definitions. Additional linking/annotation tables include tags (
            categorization), qrCodes (e.g., sample identifiers), attachments (files/links associated with items, instruments, or records), and changes (
            a provenance/audit log of recorded changes over time).

            Typical intended queries include: detecting items with undefined type (main.type = '-'), counting items by type (e.g., measurements),
            finding items whose Markdown comment or content mention a topic, listing items under a given branches.path, filtering out invisible items
            based on gui flags, and inspecting recent changes via changes and `dateModified
            """
