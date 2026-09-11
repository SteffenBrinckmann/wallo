"""Codex App Server worker helper using its JSONL stdio protocol."""
import json
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path
from typing import Any, Callable, cast

DEFAULT_CODEX_OPTIONS = {
    'executable': 'codex',
    'arg': 'app-server'
}


class CodexWorker:
    """Runs prompts through one shared Codex App Server thread."""

    def __init__(self) -> None:
        self.proc: subprocess.Popen[str] | None = None
        self.threadId = ''
        self.tmpDir = tempfile.mkdtemp(prefix='wallo-codex-')
        self.requestId = 0
        self.runtimeLock = threading.Lock()
        self.promptLock = threading.Lock()
        self.runtimeOptions = dict(DEFAULT_CODEX_OPTIONS)


    def runChat(self, work: dict[str, Any], successCb: Callable[[str], None], errorCb: Callable[[str], None]) -> None:
        """Run one prompt, preserving the Codex conversation thread."""
        def runner() -> None:
            try:
                with self.promptLock:
                    self.runtimeOptions = self.getRuntimeOptions(work)
                    self.ensureRuntime()
                    successCb(self.runPrompt(self.preparePrompt(work), work['codexModel']))
            except Exception as e:
                errorCb(str(e))
        threading.Thread(target=runner, daemon=True).start()


    def getModels(self, successCb: Callable[[list[str]], None], errorCb: Callable[[str], None]) -> None:
        """Get models available to the signed-in Codex account."""
        def runner() -> None:
            try:
                with self.promptLock:
                    self.ensureRuntime()
                    data = self.request('model/list', {})['data']
                successCb([model['model'] for model in data if not model['hidden']])
            except Exception as e:
                errorCb(str(e))
        threading.Thread(target=runner, daemon=True).start()


    def getRuntimeOptions(self, work: dict[str, Any]) -> dict[str, Any]:
        """Merge Codex service options with defaults."""
        options = dict(DEFAULT_CODEX_OPTIONS)
        options |= work.get('codexOptions', {})
        return options


    def ensureRuntime(self) -> None:
        """Start and initialize the Codex App Server once per app run."""
        with self.runtimeLock:
            if self.proc is not None and self.proc.poll() is None:
                return
            executable = self.runtimeOptions['executable']
            args = [executable, *self.runtimeOptions['arg'].split()]
            self.proc = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE,  # pylint: disable=consider-using-with
                                         stderr=subprocess.PIPE, text=True, bufsize=1)
            self.request('initialize', {'clientInfo': {'name': 'wallo', 'title': 'WALLO', 'version': '0.2.0'}})
            self.send({'method': 'initialized', 'params': {}})
            thread = self.request('thread/start', {'cwd': self.tmpDir, 'sandbox': 'read-only'})['thread']
            self.threadId = thread['id']


    def send(self, message: dict[str, Any]) -> None:
        """Write one JSON-RPC message to Codex App Server."""
        if self.proc is None or self.proc.stdin is None:
            raise RuntimeError('Codex App Server is not running')
        self.proc.stdin.write(json.dumps(message) + '\n')
        self.proc.stdin.flush()


    def request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        """Send a request and wait for its JSON-RPC result."""
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
        """Read one JSON-RPC message from the server."""
        if self.proc is None or self.proc.stdout is None:
            raise RuntimeError('Codex App Server is not running')
        line = self.proc.stdout.readline()
        if not line:
            error = self.proc.stderr.read() if self.proc.stderr is not None else ''
            raise RuntimeError(error.strip() or 'Codex App Server stopped unexpectedly')
        return cast(dict[str, Any], json.loads(line))


    def replyToServerRequest(self, message: dict[str, Any]) -> None:
        """Deny unsolicited tool approvals; WALLO uses Codex for safe text work."""
        if 'id' in message and 'method' in message:
            self.send({'id': message['id'], 'result': {'decision': 'deny'}})


    def runPrompt(self, prompt: str, model: str) -> str:
        """Start a turn and collect the streamed agent message."""
        params = {'threadId': self.threadId, 'input': [{'type': 'text', 'text': prompt}],
                  'approvalPolicy': 'never', 'sandboxPolicy': {'type': 'readOnly', 'networkAccess': False}}
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
        """Stage attached content and add optional RAG context to the prompt."""
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
        with open(Path(self.tmpDir) / 'current_prompt_context.md', 'w', encoding='utf-8') as fh:
            fh.write(prompt + ragContext + selectedText)
        return f'{prompt}{ragContext}{fileContext}{selectedText}'


    def stop(self) -> None:
        """Stop Codex App Server and remove its staged workspace."""
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
