"""LangChain-backed API chat service."""
from functools import partial
from typing import Any, Callable
from langchain_core.messages import HumanMessage, ToolMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from PySide6.QtCore import QObject, QThread, Signal  # pylint: disable=no-name-in-module
from ...configManager import ConfigurationManager
from ...pdfDocumentProcessor import extractTextFromPdf


class ApiWorker(QObject):
    """Run one API chat request in a Qt thread."""
    finished = Signal(str, str)
    error = Signal(str, str)

    def __init__(self, work: dict[str, Any]) -> None:
        """Initialize a worker for one prepared API chat request.

        Args:
            work: Prompt, LangChain client, history, and optional context inputs.
        """
        super().__init__()
        self.work = work


    def run(self) -> None:
        """Run the API chat and emit content or an error"""
        try:
            prompt = self._preparePrompt()
            agentTools = self.work['agentTools']
            if agentTools and hasattr(self.work['llmClient'], 'bind_tools'):
                content = self._runAgents(prompt)
            else:
                runnable = self.work['runnable']
                result = runnable.invoke(prompt, {'configurable': {'session_id': 'global'}})
                content = result.content if hasattr(result, 'content') else str(result)
            self.finished.emit(content, self.work['senderID'])
        except Exception as error:
            self.error.emit(str(error), self.work['senderID'])


    def _preparePrompt(self) -> str:
        """Combine prompt, retrieved context, attachment text, and selection.

        Returns:
            Text sent to the configured API model.
        """
        prompt = self.work['prompt']
        selectedText = self.work['selectedText']
        ragContext = ''
        ragRunnable = self.work['ragRunnable']
        if ragRunnable is not None:
            if retrieved := ragRunnable.retrieve(selectedText or prompt):
                ragContext = "\n\nContext:\n---\n" + '\n\n'.join(retrieved) + "\n---\n"
        fileContext = ''
        attachFilePath = self.work['attachFilePath']
        if attachFilePath.endswith('.pdf'):
            fileContext = extractTextFromPdf(attachFilePath) + '\n\n'
        if attachFilePath.split('.')[-1] in ['tex', 'txt']:
            with open(attachFilePath, 'r', encoding='utf-8') as fileHandle:
                fileContext = fileHandle.read() + '\n\n'
        return f'{prompt}{ragContext}{fileContext}{selectedText}'


    def _runAgents(self, prompt: str) -> str:
        """Run the configured tool loop for an API prompt.

        Args:
            prompt: Fully prepared user prompt.
        Returns:
            Final model reply after tool calls finish.
        """
        history = self.work['messageHistory']
        agentTools = self.work['agentTools']
        toolMap = {tool.name: tool for tool in agentTools}
        llmWithTools = self.work['llmClient'].bind_tools(agentTools)
        messages: list[Any] = list(getattr(history, 'messages', []))
        userMessage = HumanMessage(content=prompt)
        messages.append(userMessage)
        newMessages: list[Any] = [userMessage]
        for _ in range(6):
            aiMessage = llmWithTools.invoke(messages)
            messages.append(aiMessage)
            newMessages.append(aiMessage)
            toolCalls = getattr(aiMessage, 'tool_calls', None) or []
            if not toolCalls:
                break
            for toolCall in toolCalls:
                name = toolCall['name']
                try:
                    toolResult = toolMap[name].invoke(toolCall.get('args', {}))
                except Exception as error:
                    toolResult = f"Tool '{name}' failed: {str(error)}"
                toolMessage = ToolMessage(content=str(toolResult), tool_call_id=toolCall.get('id', ''))
                messages.append(toolMessage)
                newMessages.append(toolMessage)
        for message in newMessages:
            try:
                history.add_message(message)
            except Exception:
                pass
        content = messages[-1].content if hasattr(messages[-1], 'content') else str(messages[-1])
        return content


class ApiService:
    """Run LangChain API chats and own their Qt threads."""

    def __init__(self, configManager: ConfigurationManager) -> None:
        """Initialize the API service.

        Args:
            configManager: Source of the selected API service and model configuration.
        """
        self.configManager = configManager
        self.threads: list[QThread] = []
        self.workers: list[ApiWorker] = []


    @staticmethod
    def createClient(configManager: ConfigurationManager) -> Any:
        """Create a LangChain client from the selected API service.

        Args:
            configManager: Source of service credentials, provider, model, and parameters.
        Returns:
            Configured LangChain chat client.
        """
        service = configManager.get('service')
        model = configManager.get('model')
        parameter = configManager.get('parameter')
        apiKey = service['api']
        if not apiKey:
            raise ValueError('API key not configured for the service')
        if service['provider'] == 'openai':
            return ChatOpenAI(model=model, api_key=apiKey, base_url=service.get('url') or None, **parameter)
        if service['provider'] == 'gemini':
            return ChatGoogleGenerativeAI(model=model, google_api_key=apiKey, **parameter)
        raise ValueError(f"Unknown API provider '{service['provider']}'")


    def runChat(self, work: dict[str, Any], successCb: Callable[[str], None],
                errorCb: Callable[[str], None]) -> None:
        """Start an API chat in its own Qt thread.

        Args:
            work: Prepared chat inputs.
            successCb: Callback receiving generated text.
            errorCb: Callback receiving an error message.
        """
        thread = QThread()
        worker = ApiWorker(work)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(lambda content, _sender: successCb(content))
        worker.error.connect(lambda error, _sender: errorCb(error))
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        worker.error.connect(worker.deleteLater)
        thread.finished.connect(partial(self._onThreadFinished, thread, worker))
        thread.finished.connect(thread.deleteLater)
        self.threads.append(thread)
        self.workers.append(worker)
        thread.start()


    def getModels(self, successCb: Callable[[list[str]], None], _errorCb: Callable[[str], None]) -> None:
        """Return model names configured for the selected API service.

        Args:
            successCb: Callback receiving configured model names.
            _errorCb: Unused callback retained for the shared interface.
        """
        successCb(list(self.configManager.get('service').get('models', {}).keys()))


    def stop(self) -> None:
        """Request all active API chat threads to finish"""
        for thread in self.threads:
            thread.quit()
        self.threads = []
        self.workers = []


    def _onThreadFinished(self, thread: QThread, worker: ApiWorker) -> None:
        """Release references after an API worker thread exits.

        Args:
            thread: Finished Qt worker thread.
            worker: Worker previously owned by the thread.
        """
        if thread in self.threads:
            self.threads.remove(thread)
        if worker in self.workers:
            self.workers.remove(worker)
