"""ACP service with one shared session and workspace."""
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

DEFAULT_OPTIONS = {'executable': 'opencode', 'arg': 'acp'}


class AcpClient:  # pylint: disable=invalid-name
    """ACP callbacks for streamed text and permission requests."""

    def __init__(self) -> None:
        """Initialize ACP callback storage."""
        self.onUpdate: Callable[[str, Any], None] | None = None


    async def session_update(self, session_id: str, update: Any, **_kwargs: Any) -> None:
        """Forward an ACP session update to the active collector.

        Args:
            session_id: ACP session that produced the update.
            update: Protocol update payload.
            _kwargs: Unused protocol callback fields.
        """
        if self.onUpdate is not None:
            self.onUpdate(session_id, update)


    async def request_permission(self, options: list[Any], _sessionId: str, _toolCall: Any,
                                 **_kwargs: Any) -> dict[str, dict[str, str]]:
        """Reject every ACP tool permission request.

        Args:
            options: Permission choices supplied by the agent.
            _sessionId: Session requesting permission.
            _toolCall: Tool invocation requesting permission.
            _kwargs: Unused protocol callback fields.
        Returns:
            Cancellation response required by ACP.
        """
        del options
        return {'outcome': {'outcome': 'cancelled'}}


class AcpService:
    """Run ACP prompts through one serialized session."""

    def __init__(self) -> None:
        """Initialize an inactive ACP service and temporary workspace."""
        self.client: AcpClient | None = None
        self.connection: Any = None
        self.spawnContext: Any = None
        self.sessionId = ''
        self.tmpDir = tempfile.mkdtemp(prefix='wallo-acp-')
        self.loop: asyncio.AbstractEventLoop | None = None
        self.loopThread: threading.Thread | None = None
        self.initLock = threading.Lock()
        self.promptLock: asyncio.Lock | None = None
        self.options = dict(DEFAULT_OPTIONS)


    def runChat(self, work: dict[str, Any], successCb: Callable[[str], None],
                errorCb: Callable[[str], None]) -> None:
        """Start one serialized ACP chat request.

        Args:
            work: Prepared prompt, context, attachment, and service options.
            successCb: Callback receiving generated text.
            errorCb: Callback receiving an error message.
        """
        prompt = self.preparePrompt(work)
        if self.connection is None or not self.sessionId:
            self.options = dict(DEFAULT_OPTIONS) | work.get('serviceOptions', {})

        def runner() -> None:
            try:
                self.ensureRuntime()
                if self.loop is None:
                    raise RuntimeError('ACP loop not initialized')
                content = asyncio.run_coroutine_threadsafe(self.runPrompt(prompt), self.loop).result()
                successCb(content)
            except Exception as error:
                errorCb(str(error))
        threading.Thread(target=runner, daemon=True).start()


    def getModels(self, successCb: Callable[[list[str]], None], _errorCb: Callable[[str], None]) -> None:
        """Report that ACP does not expose a WALLO model selector.

        Args:
            successCb: Callback receiving an empty model list.
            _errorCb: Unused callback retained for the common interface.
        """
        successCb([])


    def ensureRuntime(self) -> None:
        """Start the ACP loop and session if they are not running.
        """
        with self.initLock:
            if self.loop is None:
                self.loop = asyncio.new_event_loop()
                self.loopThread = threading.Thread(target=self._runLoop, daemon=True)
                self.loopThread.start()
            if self.connection is None or not self.sessionId:
                if self.loop is None:
                    raise RuntimeError('ACP loop not initialized')
                asyncio.run_coroutine_threadsafe(self.startSession(), self.loop).result()


    def stop(self) -> None:
        """Close the ACP session, loop, and temporary workspace"""
        self.sessionId = ''
        if self.loop is not None and self.spawnContext is not None:
            try:
                future = asyncio.run_coroutine_threadsafe(self.spawnContext.__aexit__(None, None, None), self.loop)
                future.result(timeout=5)
            except Exception:
                pass
        if self.loop is not None:
            self.loop.call_soon_threadsafe(self.loop.stop)
        if self.loopThread is not None:
            self.loopThread.join(timeout=2)
        self.connection = None
        self.spawnContext = None
        self.client = None
        self.promptLock = None
        self.loop = None
        self.loopThread = None
        if self.tmpDir and os.path.isdir(self.tmpDir):
            shutil.rmtree(self.tmpDir, ignore_errors=True)


    def _runLoop(self) -> None:
        """Run the dedicated ACP asyncio loop.
        """
        if self.loop is not None:
            asyncio.set_event_loop(self.loop)
            self.loop.run_forever()


    async def startSession(self) -> None:
        """Spawn the configured ACP agent and open one session.
        """
        if self.connection is not None and self.sessionId:
            return
        if spawnAgentProcess is None or textBlock is None:
            raise RuntimeError('Agent Client Protocol SDK required: pip install agent-client-protocol')
        self.client = AcpClient()
        self.spawnContext = cast(Any, spawnAgentProcess)(self.client, self.options['executable'],
                                                            self.options['arg'], '--cwd', self.tmpDir)
        self.connection, _ = await self.spawnContext.__aenter__() # pylint: disable=unnecessary-dunder-call
        await self.connection.initialize(protocol_version=PROTOCOL_VERSION)
        session = await self.connection.new_session(cwd=self.tmpDir, mcp_servers=[])
        self.sessionId = session.session_id
        self.promptLock = asyncio.Lock()


    async def runPrompt(self, prompt: str) -> str:
        """Send a prompt and collect streamed ACP message chunks.

        Args:
            prompt: Fully prepared ACP prompt.
        Returns:
            Combined agent response text.
        """
        if self.connection is None or self.client is None or not self.sessionId:
            raise RuntimeError('ACP runtime not initialized')
        if self.promptLock is None:
            self.promptLock = asyncio.Lock()
        parts: list[str] = []

        def onUpdate(sessionId: str, update: Any) -> None:
            if sessionId == self.sessionId and getattr(update, 'session_update', '') == 'agent_message_chunk':
                content = getattr(update, 'content', None)
                text = getattr(content, 'text', '') if content is not None else ''
                if text:
                    parts.append(text)
        async with self.promptLock:
            self.client.onUpdate = onUpdate
            await self.connection.prompt(session_id=self.sessionId, prompt=[textBlock(prompt)], message_id=str(uuid4()))
            self.client.onUpdate = None
        return ''.join(parts).strip()


    def preparePrompt(self, work: dict[str, Any]) -> str:
        """Stage attachments and build the ACP prompt.

        Args:
            work: Prepared chat inputs including optional RAG and attachment context.
        Returns:
            Prompt text restricted to the ACP temporary workspace.
        """
        prompt = work['prompt']
        selectedText = work['selectedText']
        ragContext = self._ragContext(work['ragRunnable'], selectedText or prompt)
        fileContext = ''
        if attachFilePath := work['attachFilePath']:
            target = Path(self.tmpDir) / Path(attachFilePath).name
            if target.resolve() != Path(attachFilePath).resolve():
                shutil.copy2(attachFilePath, target)
            fileContext = f'\n\nAttached file staged at: {target.name}\n'
        with open(Path(self.tmpDir) / 'current_prompt_context.md', 'w', encoding='utf-8') as fileHandle:
            fileHandle.write(prompt + ragContext + selectedText)
        return f'{prompt}{ragContext}{fileContext}{selectedText}\n\nUse files only inside: {self.tmpDir}'


    @staticmethod
    def _ragContext(ragRunnable: Any, query: str) -> str:
        """Build optional RAG context for an ACP prompt.

        Args:
            ragRunnable: Retrieval object or None.
            query: Prompt text used for retrieval.
        Returns:
            Formatted context block, or an empty string.
        """
        if ragRunnable is not None and (retrieved := ragRunnable.retrieve(query)):
            return "\n\nContext:\n---\n" + '\n\n'.join(retrieved) + "\n---\n"
        return ''
