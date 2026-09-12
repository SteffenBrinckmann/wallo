"""Codex App Server service using its JSONL stdio protocol."""
import json
import shlex
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path
from typing import Any, Callable, cast

DEFAULT_OPTIONS = {'executable': 'codex', 'arg': 'app-server'}


class CodexService:
    """Run prompts through one shared Codex App Server thread."""

    def __init__(self) -> None:
        """Initialize an inactive Codex App Server service."""
        self.proc: subprocess.Popen[str] | None = None
        self.threadId = ''
        self.tmpDir = tempfile.mkdtemp(prefix='wallo-codex-')
        self.requestId = 0
        self.runtimeLock = threading.Lock()
        self.promptLock = threading.Lock()
        self.options = dict(DEFAULT_OPTIONS)


    def runChat(self, work: dict[str, Any], successCb: Callable[[str], None],
                errorCb: Callable[[str], None]) -> None:
        """Start one serialized Codex chat request.

        Args:
            work: Prepared prompt, context, attachment, model, and service options.
            successCb: Callback receiving generated text.
            errorCb: Callback receiving an error message.
        """
        def runner() -> None:
            try:
                with self.promptLock:
                    self.options = dict(DEFAULT_OPTIONS) | work.get('serviceOptions', {})
                    self.ensureRuntime()
                    successCb(self.runPrompt(self.preparePrompt(work), work['model']))
            except Exception as error:
                errorCb(str(error))
        threading.Thread(target=runner, daemon=True).start()


    def getModels(self, successCb: Callable[[list[str]], None], errorCb: Callable[[str], None]) -> None:
        """Fetch models available from the signed-in Codex account.

        Args:
            successCb: Callback receiving visible model names.
            errorCb: Callback receiving an error message.
        """
        def runner() -> None:
            try:
                with self.promptLock:
                    self.ensureRuntime()
                    data = self.request('model/list', {})['data']
                successCb([model['model'] for model in data if not model['hidden']])
            except Exception as error:
                errorCb(str(error))
        threading.Thread(target=runner, daemon=True).start()


    def ensureRuntime(self) -> None:
        """Start and initialize the Codex App Server if needed.
        """
        with self.runtimeLock:
            if self.proc is not None and self.proc.poll() is None:
                return
            args = [self.options['executable'], *shlex.split(self.options['arg'])]
            self.proc = subprocess.Popen( # pylint: disable=consider-using-with
                args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                text=True, bufsize=1)
            self.request('initialize', {'clientInfo': {'name': 'wallo', 'title': 'WALLO', 'version': '0.2.0'}})
            self.send({'method': 'initialized', 'params': {}})
            self.threadId = self.request('thread/start', {'cwd': self.tmpDir, 'sandbox': 'read-only'})['thread']['id']


    def send(self, message: dict[str, Any]) -> None:
        """Write one JSON-RPC message to Codex.

        Args:
            message: JSON-RPC request or response payload.
        """
        if self.proc is None or self.proc.stdin is None:
            raise RuntimeError('Codex App Server is not running')
        self.proc.stdin.write(json.dumps(message) + '\n')
        self.proc.stdin.flush()


    def request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        """Send a JSON-RPC request and wait for its response.

        Args:
            method: Codex App Server method name.
            params: Parameters for the method.
        Returns:
            Server result object.
        """
        self.requestId += 1
        requestId = self.requestId
        self.send({'method': method, 'id': requestId, 'params': params})
        while True:
            message = self.readMessage()
            if message.get('id') != requestId:
                self.replyToServerRequest(message)
                continue
            if 'error' in message:
                raise RuntimeError(message['error'].get('message', 'Codex App Server request failed'))
            return cast(dict[str, Any], message['result'])


    def readMessage(self) -> dict[str, Any]:
        """Read one JSON-RPC message from Codex stdout.

        Returns:
            Decoded JSON-RPC message.
        """
        if self.proc is None or self.proc.stdout is None:
            raise RuntimeError('Codex App Server is not running')
        if line := self.proc.stdout.readline():
            return cast(dict[str, Any], json.loads(line))
        raise RuntimeError('Codex App Server stopped unexpectedly')


    def replyToServerRequest(self, message: dict[str, Any]) -> None:
        """Deny unsolicited Codex tool approvals.

        Args:
            message: Server request that may require a denial response.
        """
        if 'id' in message and 'method' in message:
            self.send({'id': message['id'], 'result': {'decision': 'deny'}})


    def runPrompt(self, prompt: str, model: str) -> str:
        """Run a Codex turn and collect its streamed text.

        Args:
            prompt: Fully prepared prompt.
            model: Optional selected Codex model.
        Returns:
            Combined agent response text.
        """
        params: dict[str, Any] = {
            'threadId': self.threadId, 'input': [{'type': 'text', 'text': prompt}],
            'approvalPolicy': 'never', 'sandboxPolicy': {'type': 'readOnly', 'networkAccess': False}
        }
        if model:
            params['model'] = model
        turn = self.request('turn/start', params)['turn']
        parts: list[str] = []
        while True:
            message = self.readMessage()
            if message.get('method') == 'item/agentMessage/delta':
                parts.append(message['params']['delta'])
            if message.get('method') == 'turn/completed' and message['params']['turn']['id'] == turn['id']:
                if message['params']['turn']['status'] != 'completed':
                    raise RuntimeError(f"Codex turn {message['params']['turn']['status']}")
                return ''.join(parts).strip()
            self.replyToServerRequest(message)


    def preparePrompt(self, work: dict[str, Any]) -> str:
        """Stage attachments and build a Codex prompt.

        Args:
            work: Prepared chat inputs including optional RAG and attachment context.
        Returns:
            Prompt text sent to Codex.
        """
        prompt = work['prompt']
        selectedText = work['selectedText']
        ragContext = ''
        if ragRunnable := work['ragRunnable']:
            if retrieved := ragRunnable.retrieve(selectedText or prompt):
                ragContext = f"\n\nContext:\n---\n{ '\n\n'.join(retrieved) }\n---\n"
        fileContext = ''
        if attachFilePath := work['attachFilePath']:
            target = Path(self.tmpDir) / Path(attachFilePath).name
            if target.resolve() != Path(attachFilePath).resolve():
                shutil.copy2(attachFilePath, target)
            fileContext = f'\n\nAttached file staged at: {target.name}\n'
        with open(Path(self.tmpDir) / 'current_prompt_context.md', 'w', encoding='utf-8') as fileHandle:
            fileHandle.write(prompt + ragContext + selectedText)
        return f'{prompt}{ragContext}{fileContext}{selectedText}'


    def stop(self) -> None:
        """Stop Codex and remove its temporary workspace.
        """
        if self.proc is not None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        self.proc = None
        self.threadId = ''
        if self.tmpDir and Path(self.tmpDir).is_dir():
            shutil.rmtree(self.tmpDir, ignore_errors=True)
