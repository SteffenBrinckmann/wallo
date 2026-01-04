"""LLM processing and interaction logic for the Wallo application.
- All LLM logic is here
"""
from typing import Any, Optional
from langchain_openai import ChatOpenAI
from langchain_community.document_loaders.parsers.audio import OpenAIWhisperParser
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.documents.base import Blob
from langchain_core.messages import SystemMessage
from langchain_core.runnables.history import RunnableWithMessageHistory
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
        self.systemPrompt = 'You are a helpful assistant.'
        self.messageHistory = InMemoryChatMessageHistory()
        self.systemPromptInjected = False
        self.runnable:None|RunnableWithMessageHistory = None
        self.ragIndexer = RagIndexer(configManager)


    def createClientFromConfig(self, serviceConfig: dict[str,str]) -> Any:
        """Create a LangChain LLM from service config.

        Supported types:
        - openai (OpenAI + compatible endpoints)
        - gemini (Google Gemini)
        """
        serviceType = serviceConfig['type']
        model       = serviceConfig['model']
        apiKey      = serviceConfig['api']
        baseUrl     = serviceConfig.get('url') or None  #None if url-string==''
        if not apiKey:
            raise ValueError('API key not configured for the service')
        if serviceType == 'openAI':
            return ChatOpenAI(model=model, api_key=apiKey, base_url=baseUrl, temperature=0.7) # type: ignore[arg-type]
        if serviceType == 'Gemini':
            return ChatGoogleGenerativeAI(model=model, google_api_key=apiKey, temperature=0.7)
        raise ValueError(f"Unknown service type '{serviceType}'")


    def setSystemPrompt(self, promptName: str) -> None:
        """Set (and re-inject) the system prompt to be used by the LLM.

        When the system prompt changes, it is appended as a new SystemMessage
        so the conversation continues chronologically.
        """
        systemPrompts = self.configManager.get('system-prompts')
        for prompt in systemPrompts:
            if prompt['name'] == promptName:
                self.systemPrompt = prompt['system-prompt']
                try:
                    self.messageHistory.add_message(SystemMessage(content=self.systemPrompt))
                    self.systemPromptInjected = True
                except Exception:
                    self.systemPromptInjected = False
                return
        raise ValueError(f"System prompt '{promptName}' not found in configuration")


    def processPrompt(self, senderID:str, promptName: str, serviceName: str,
                      selectedText: str = '', pdfFilePath: str = '',
                      inquiryResponse: str = '', ragUsage: bool = False) -> dict[str, Any]:
        """Process a prompt based on its attachment type.

        Args:
            promptName: Name of the prompt to use.
            serviceName: Name of the service to use.
            selectedText: Selected text from the editor.
            pdfFilePath: Path to the PDF file.
            inquiryResponse: User's response to the inquiry.
            ragUsage: Whether to use RAG for retrieval.

        Returns:
            Dictionary with processing parameters for the worker.

        Raises:
            ValueError: If prompt or service is not found.
        """
        serviceConfig = self.configManager.getServiceByName(serviceName)
        if not serviceConfig:
            raise ValueError(f"Service '{serviceName}' not found in configuration")
        llm = self.createClientFromConfig(serviceConfig)

        # Prepare prompt configuration if needed
        promptConfig: dict[str, Any] = {}
        promptConfig = self.configManager.getPromptByName(promptName)
        if not promptConfig:
            raise ValueError(f"Prompt '{promptName}' not found in configuration")
        attachmentType = promptConfig['attachment']
        promptHeader = f"{promptConfig['user-prompt']}\\n" if promptConfig['user-prompt'] else ''

        # since LLM is defined, check if message-history defined. If not, define it
        if self.runnable is None:
            self.runnable = RunnableWithMessageHistory(llm, lambda: self.messageHistory)

        # RAG retrieval
        ragContext = ''
        if ragUsage:
            if retrieved:= self.ragIndexer.retrieve(selectedText or promptHeader): #get list of strings from RAG database
                print('RAG context:', '\n\n'.join(retrieved))
                ragContext = f"\n\nContext:\n---\n{'\n\n'.join(retrieved)}\n---\n"

        # Assemble work for 2nd thread based on task
        result = {'runnable': self.runnable, 'prompt': None, 'senderID': senderID}
        if attachmentType == 'selection':
            fullPrompt = f"{promptHeader}{ragContext}{selectedText}"
            result['prompt'] = fullPrompt
        elif attachmentType == 'pdf':
            fullPrompt = f"{promptConfig['user-prompt']}\n{ragContext}"
            result['prompt'] = fullPrompt
            result['fileName'] = pdfFilePath
        elif attachmentType == 'inquiry':
            inquiryText = promptConfig['user-prompt'].split('|')[1]
            processedPrompt = promptConfig['user-prompt'].replace(f'|{inquiryText}|', inquiryResponse)
            fullPrompt = f"{processedPrompt}\n\n{ragContext}{selectedText}\n"
            result['prompt'] = fullPrompt
        else:
            raise ValueError(f"Unknown attachment type '{attachmentType}' for prompt '{promptName}'")
        return result


    def getInquiryText(self, promptName: str) -> Optional[str]:
        """Get the inquiry text for a prompt.

        Args:
            promptName: Name of the prompt to check.

        Returns:
            Inquiry text if found, None otherwise.
        """
        promptConfig = self.configManager.getPromptByName(promptName)
        if not promptConfig or promptConfig['attachment'] != 'inquiry':
            return None
        try:
            userPrompt = promptConfig['user-prompt']
            if isinstance(userPrompt, str):
                return userPrompt.split('|')[1]
            return None
        except (IndexError, AttributeError):
            return None


    def processLLMResponse(self, content: str) -> str:
        """Process and clean LLM response content.

        Args:
            content: Raw content from the LLM response.

        Returns:
            Cleaned and processed content.
        """
        content = content.strip()
        # Remove code block markers if present
        if content.endswith('```'):
            content = content[:-3].strip()
        if content.startswith('```'):
            content = content.split('\n', 1)[-1].strip()
        return content


    def transcribeAudio(self, audioFilePath:str) -> str:
        """ Transcribe audio to string using LLM
        Args:
            audioFilePath (str): The path to the audio file .wav
        Returns:
            str: The transcribed text.
        """
        #TODO P2 move to Backend thread
        try:
            possOpenAI = self.configManager.getOpenAiServices()
            if not possOpenAI:
                return 'No OpenAI services configured'
            parser = OpenAIWhisperParser(api_key=self.configManager.getServiceByName(possOpenAI[0])['api'])
            blob = Blob.from_path(audioFilePath)
            docs = parser.parse(blob)
            if not docs:
                return ''
            return docs[0].page_content
        except Exception as e:
            return f'[STT failed: {e}]'
