"""LLM processing and interaction logic for the Wallo application.
- All LLM logic is here
"""
from typing import Any
from langchain_community.document_loaders.parsers.audio import OpenAIWhisperParser
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.messages import SystemMessage
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from PySide6.QtWidgets import QMessageBox  # pylint: disable=no-name-in-module
from .agents import Agents
from .configManager import ConfigurationManager
from .ragIndexer import RagIndexer


class LLMProcessor:
    """Handles LLM API interactions and prompt processing."""

    def __init__(self, configManager: ConfigurationManager) -> None:
        """Initialize the LLM processor.

        Args:
            configManager: Configuration manager instance.
        """
        self.configManager = configManager
        self.systemPrompt = self.configManager.get('system-prompt')
        self.messageHistory = InMemoryChatMessageHistory()
        self.systemPromptInjected = False
        self._injectSystemPrompt(self.systemPrompt)
        self.runnable: RunnableWithMessageHistory | None = None
        # TODO P4 system of services for RAG, TTS and STT: all from one provider?
        # Temporary openAI services only
        # currently, only OpenAI embeddings are implemented, get those that quality
        # Future: user chooses service to use for RAG, always. Configuration changes to save for that
        # then this preference is used during this initiation
        possOpenAI = self.configManager.getOpenAiServices()
        if not possOpenAI:
            QMessageBox.critical(None, 'Configuration error', 'No OpenAI services configured')
            return
        apiKey = self.configManager.getServiceByName(possOpenAI[0])['api']
        self.sttParser = OpenAIWhisperParser(api_key=apiKey)
        self.ragIndexer = RagIndexer(apiKey)
        self.agents = Agents()


    def _injectSystemPrompt(self, prompt: str) -> None:
        """Inject a system prompt into the message history."""
        self.systemPromptInjected = False
        try:
            self.messageHistory.add_message(SystemMessage(content=prompt))
            self.systemPromptInjected = True
        except Exception:
            pass


    def createClientFromConfig(self) -> Any:
        """Create a LangChain LLM from service config.

        Supported types:
        - openai (OpenAI + compatible endpoints)
        - gemini (Google Gemini)
        """
        service = self.configManager.get('service')
        serviceType = service['type']
        model       = self.configManager.get('model')
        parameter   = self.configManager.get('parameter')
        apiKey      = service['api']
        baseUrl     = service.get('url') or None  #None if url-string==''
        if not apiKey:
            raise ValueError('API key not configured for the service')
        if serviceType == 'openAI':
            return ChatOpenAI(model=model, api_key=apiKey, base_url=baseUrl, **parameter)
        if serviceType == 'Gemini':
            return ChatGoogleGenerativeAI(model=model, google_api_key=apiKey, **parameter)
        raise ValueError(f"Unknown service type '{serviceType}'")


    def setSystemPrompt(self, promptName: str) -> None:
        """Set (and re-inject) the system prompt to be used by the LLM.

        When the system prompt changes, it is appended as a new SystemMessage
        so the conversation continues chronologically.
        """
        for prompt in self.configManager.get('system-prompts'):
            if prompt['name'] == promptName:
                self.systemPrompt = prompt['system-prompt']
                if self.agents.useAgents:
                    self.systemPrompt += '\n\n' + self.agents.getAgentCoordinatorPrompt()
                self._injectSystemPrompt(self.systemPrompt)
                return
        raise ValueError(f"System prompt '{promptName}' not found in configuration")


    def processPrompt(self, senderID: str, promptName: str, selectedText: str = '', attachFilePath: str = '',
                      inquiryResponse: str = '', ragUsage: bool = False) -> dict[str, Any]:
        """Process a prompt based on its attachment type.

        Args:
            promptName: Name of the prompt to use.
            serviceName: Name of the service to use.
            selectedText: Selected text from the editor.
            attachFilePath: Path to the PDF file.
            inquiryResponse: User's response to the inquiry.
            ragUsage: Whether to use RAG for retrieval.

        Returns:
            Dictionary with processing parameters for the worker.

        Raises:
            ValueError: If prompt or service is not found.
        """
        llm = self.createClientFromConfig()
        # since LLM is defined, check if message-history defined. If not, define it
        if self.runnable is None:
            self.runnable = RunnableWithMessageHistory(llm, lambda: self.messageHistory)
        # Prepare prompt configuration
        promptConfig: dict[str, Any] = self.configManager.getPromptByName(promptName)
        prompt = f"{promptConfig['user-prompt']}\\n" if promptConfig['user-prompt'] else ''
        if promptConfig['inquiry']:
            inquiryText = promptConfig['user-prompt'].split('|')[1]
            prompt = promptConfig['user-prompt'].replace(f'|{inquiryText}|', inquiryResponse)

        # return work for 2nd thread based on task
        return {
            'runnable'      : self.runnable,
            'llmClient'     : llm,
            'messageHistory': self.messageHistory,
            'prompt'        : prompt,
            'senderID'      : senderID,
            'selectedText'  : selectedText,
            'attachFilePath': attachFilePath,
            'ragRunnable'   : self.ragIndexer if ragUsage else None,
            'agentTools'    : self.agents.getAgentTools()
        }


    def processLLMResponse(self, content: str) -> str:
        """Process and clean LLM response content.
        - Remove code block markers if present

        Args:
            content: Raw content from the LLM response.

        Returns:
            Cleaned and processed content.
        """
        content = content.strip()
        if content.startswith('```'):
            content = content.split('\n', 1)[-1].strip()
        if content.endswith('```'):
            content = content[:-3].rstrip()
        # horizontal rule(s) included
        if '\n---\n' in content:
            content = content.split('\n---\n')[1].strip()
        # all replace
        content = content.replace('~~','~').replace('\\\\', '\\')
        return content.strip()
