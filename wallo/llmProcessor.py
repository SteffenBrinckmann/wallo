"""LLM processing and interaction logic for the Wallo application."""
import re
from typing import Any, Optional
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from .configFileManager import ConfigurationManager

class LLMProcessor:
    """Handles LLM API interactions and prompt processing."""

    def __init__(self, configManager: ConfigurationManager) -> None:
        """Initialize the LLM processor.

        Args:
            configManager: Configuration manager instance.
        """
        self.configManager = configManager
        self.systemPrompt = 'You are a helpful assistant.'
        #TODO change to langchain
        self.conversations: dict[str, list[dict[str, str]]] = {}


    def createClientFromConfig(self, serviceConfig: dict):
        """Create a LangChain LLM from service config.

        Supported types:
        - openai (OpenAI + compatible endpoints)
        - gemini (Google Gemini)
        """
        serviceType = serviceConfig.get('type', 'openai')
        model = serviceConfig.get('model')
        apiKey = serviceConfig.get('api')
        baseUrl = serviceConfig.get('url') or None
        if not apiKey:
            raise ValueError('API key not configured for the service')
        if serviceType == 'openai':
            return ChatOpenAI(model=model, api_key=apiKey, base_url=baseUrl, temperature=0.7)
        if serviceType == 'gemini':
            return ChatGoogleGenerativeAI(model=model, google_api_key=apiKey, temperature=0.7)
        raise ValueError(f"Unknown service type '{serviceType}'")


    def setSystemPrompt(self, promptName: str) -> None:
        """Set the system prompt to be used by the LLM.

        Args:
            promptName: Name of the system prompt to use.

        Raises:
            ValueError: If system prompt is not found.
        """
        systemPrompts = self.configManager.get('system-prompts')
        for prompt in systemPrompts:
            if prompt['name'] == promptName:
                self.systemPrompt = prompt['system-prompt']
                return
        raise ValueError(f"System prompt '{promptName}' not found in configuration")


    def processPrompt(self, senderID:str, promptName: str, serviceName: str,
                      selectedText: str = '', pdfFilePath: str = '',
                      inquiryResponse: str = '') -> dict[str, Any]:
        """Process a prompt based on its attachment type.

        Args:
            promptName: Name of the prompt to use.
            serviceName: Name of the service to use.
            selectedText: Selected text from the editor.
            pdfFilePath: Path to the PDF file.
            inquiryResponse: User's response to the inquiry.

        Returns:
            Dictionary with processing parameters for the worker.

        Raises:
            ValueError: If prompt or service is not found.
        """
        if not re.match(r'^[0-9a-f]{32}$', senderID):
            raise ValueError(f"SenderID '{senderID}' is not a valid uuid4")
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
        promptHeader = f"{promptConfig['user-prompt']}\\n"

        result = {'senderID': senderID, 'llm': llm, 'systemPrompt': self.systemPrompt}
        if self.responseID:
            result['previousPromptId'] = self.responseID
        if attachmentType == 'selection':
            fullPrompt = f"{promptHeader}{selectedText}"
            result['prompt'] = fullPrompt
        elif attachmentType == 'pdf':
            fullPrompt = f"{promptConfig['user-prompt']}\\n"
            result['prompt'] = fullPrompt
            result['fileName'] = pdfFilePath
        elif attachmentType == 'inquiry':
            inquiryText = promptConfig['user-prompt'].split('|')[1]
            processedPrompt = promptConfig['user-prompt'].replace(f'|{inquiryText}|', inquiryResponse)
            fullPrompt = f"{processedPrompt}\\n\\n{selectedText}\\n"
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
