"""ACP worker helper for shared session communication."""
import asyncio
import os
import shutil
import tempfile
import threading
from pathlib import Path
from typing import Any, Callable, cast
from uuid import uuid4

PROTOCOL_VERSION: int
spawnAgentProcess: Any
textBlock: Any
try:
    from acp import PROTOCOL_VERSION as _PROTOCOL_VERSION
    from acp import spawn_agent_process as _spawn_agent_process
    from acp import text_block as _text_block
    PROTOCOL_VERSION = _PROTOCOL_VERSION
    spawnAgentProcess = _spawn_agent_process
    textBlock = _text_block
except ImportError:
    PROTOCOL_VERSION = 1
    spawnAgentProcess = None
    textBlock = None

DEFAULT_ACP_OPTIONS = {
    'executable': 'opencode',
    'arg': 'acp'
}

class ACPClient:  # pylint: disable=invalid-name
    """ACP client callback implementation for streaming updates and permissions."""
    def __init__(self) -> None:
        self.onUpdate: Callable[[str, Any], None] | None = None


    async def session_update(self, session_id: str, update: Any, **_kwargs: Any) -> None:
        """Handle ACP session updates."""
        if self.onUpdate is not None:
            self.onUpdate(session_id, update)


    async def request_permission(self, options: list[Any], _session_id: str, _tool_call: Any,
                                 **_kwargs: Any) -> dict[str, dict[str, str]]:
        """Select the first offered ACP permission option."""
        return {'outcome': {'outcome': 'selected', 'optionId': options[0].option_id}}


class ACPWorker:
    """Runs ACP prompts with shared temp dir and session."""

    def __init__(self) -> None:
        self.acpClient: ACPClient | None = None
        self.acpConn: Any = None
        self.acpProc: Any = None
        self.acpSpawnCtx: Any = None
        self.acpSessionId = ''
        self.acpTmpDir = tempfile.mkdtemp(prefix='wallo-acp-')
        self.acpLoop: asyncio.AbstractEventLoop | None = None
        self.acpThread: threading.Thread | None = None
        self.acpInitLock = threading.Lock()
        self.acpPromptLock: asyncio.Lock | None = None
        self.runtimeOptions = dict(DEFAULT_ACP_OPTIONS)


    def runChat(self, work: dict[str, Any], successCb: Callable[[str], None], errorCb: Callable[[str], None]) -> None:
        """Run ACP prompt path with a shared session and serialized prompts."""
        prompt = self.preparePrompt(work)
        if self.acpConn is None or not self.acpSessionId:
            self.runtimeOptions = self.getRuntimeOptions(work)
        def runner() -> None:
            try:
                self.ensureRuntime()
                if self.acpLoop is None:
                    raise RuntimeError('ACP loop not initialized')
                future = asyncio.run_coroutine_threadsafe(self.runPrompt(prompt), self.acpLoop)
                content = future.result()
                successCb(content)
            except Exception as e:
                errorCb(str(e))
        thread = threading.Thread(target=runner, daemon=True)
        thread.start()


    def ensureRuntime(self) -> None:
        """Start ACP event loop, process and session once per app run."""
        with self.acpInitLock:
            if self.acpLoop is None:
                self.acpLoop = asyncio.new_event_loop()
                self.acpThread = threading.Thread(target=self.acpLoopRunner, daemon=True)
                self.acpThread.start()
            if self.acpConn is None or not self.acpSessionId:
                if self.acpLoop is None:
                    raise RuntimeError('ACP loop not initialized')
                future = asyncio.run_coroutine_threadsafe(self.startSession(), self.acpLoop)
                future.result()


    def getRuntimeOptions(self, work: dict[str, Any]) -> dict[str, Any]:
        """Merge ACP service options with defaults."""
        options = dict(DEFAULT_ACP_OPTIONS)
        options.update(work.get('acpOptions', {}))
        return options


    def acpLoopRunner(self) -> None:
        """Run dedicated asyncio loop for ACP communication."""
        if self.acpLoop is None:
            return
        asyncio.set_event_loop(self.acpLoop)
        self.acpLoop.run_forever()


    async def startSession(self) -> None:
        """Create one ACP connection and one session."""
        if self.acpConn is not None and self.acpSessionId:
            return
        if spawnAgentProcess is None or textBlock is None:
            raise RuntimeError('ACP requires the Agent Client Protocol SDK: python -m pip install agent-client-protocol')
        self.acpClient = ACPClient()
        executable = self.runtimeOptions['executable']
        arg = self.runtimeOptions['arg']
        self.acpSpawnCtx = cast(Any, spawnAgentProcess)(self.acpClient, executable, arg, '--cwd', self.acpTmpDir)
        # Keep the async context open for the whole app session.
        self.acpConn, self.acpProc = await self.acpSpawnCtx.__aenter__() # pylint: disable=unnecessary-dunder-call
        await self.acpConn.initialize(protocol_version=PROTOCOL_VERSION)
        session = await self.acpConn.new_session(cwd=self.acpTmpDir, mcp_servers=[])
        self.acpSessionId = session.session_id
        self.acpPromptLock = asyncio.Lock()


    async def runPrompt(self, prompt: str) -> str:
        """Send a prompt via ACP and collect streamed answer chunks."""
        if self.acpConn is None or self.acpClient is None or not self.acpSessionId:
            raise RuntimeError('ACP runtime not initialized')
        if self.acpPromptLock is None:
            self.acpPromptLock = asyncio.Lock()
        parts: list[str] = []

        def onUpdate(sessionId: str, update: Any) -> None:
            if sessionId != self.acpSessionId:
                return
            if getattr(update, 'session_update', '') != 'agent_message_chunk':
                return
            content = getattr(update, 'content', None)
            text = getattr(content, 'text', '') if content is not None else ''
            if text:
                parts.append(text)

        async with self.acpPromptLock:
            self.acpClient.onUpdate = onUpdate
            await self.acpConn.prompt(session_id=self.acpSessionId, prompt=[textBlock(prompt)], message_id=str(uuid4()))
            self.acpClient.onUpdate = None
        return ''.join(parts).strip()


    def preparePrompt(self, work: dict[str, Any]) -> str:
        """Create ACP prompt and stage optional file context into temp workspace."""
        prompt = work['prompt']
        selectedText = work['selectedText']
        ragRunnable = work['ragRunnable']
        ragContext = ''
        if ragRunnable is not None:
            if retrieved := ragRunnable.retrieve(selectedText or prompt):
                ragContext = f"\n\nContext:\n---\n{ '\n\n'.join(retrieved) }\n---\n"
        fileContext = ''
        if attachFilePath := work['attachFilePath']:
            safeName = Path(attachFilePath).name
            target = Path(self.acpTmpDir) / safeName
            if target.resolve() != Path(attachFilePath).resolve():
                shutil.copy2(attachFilePath, target)
            fileContext = f'\n\nAttached file staged at: {target.name}\n'
        stagedText = Path(self.acpTmpDir) / 'current_prompt_context.md'
        with open(stagedText, 'w', encoding='utf-8') as fh:
            fh.write(prompt + ragContext + selectedText)
        return f"{prompt}{ragContext}{fileContext}{selectedText}\n\nUse files only inside: {self.acpTmpDir}"


    def stop(self) -> None:
        """Stop ACP resources and remove temp workspace."""
        self.acpSessionId = ''
        if self.acpLoop is not None and self.acpSpawnCtx is not None:
            try:
                future = asyncio.run_coroutine_threadsafe(self.acpSpawnCtx.__aexit__(None, None, None), self.acpLoop)
                future.result(timeout=5)
            except Exception:
                pass
        if self.acpLoop is not None:
            self.acpLoop.call_soon_threadsafe(self.acpLoop.stop)
        if self.acpThread is not None:
            self.acpThread.join(timeout=2)
        self.acpConn = None
        self.acpProc = None
        self.acpSpawnCtx = None
        self.acpClient = None
        self.acpPromptLock = None
        self.acpLoop = None
        self.acpThread = None
        if self.acpTmpDir and os.path.isdir(self.acpTmpDir):
            shutil.rmtree(self.acpTmpDir, ignore_errors=True)
