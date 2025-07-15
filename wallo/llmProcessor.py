"""LLM processing and interaction logic for the Wallo application."""
from typing import Dict, Any, Optional
from openai import OpenAI
from .configManager import ConfigurationManager

class LLMProcessor:
    """Handles LLM API interactions and prompt processing."""

    def __init__(self, configManager: ConfigurationManager) -> None:
        """Initialize the LLM processor.

        Args:
            configManager: Configuration manager instance.
        """
        self.configManager = configManager


    def createClient(self, serviceName: str) -> OpenAI:
        """Create an OpenAI client for the specified service.

        Args:
            serviceName: Name of the service to use.

        Returns:
            OpenAI client instance.

        Raises:
            ValueError: If service is not found or API key is missing.
        """
        serviceConfig = self.configManager.getServiceByName(serviceName)
        if not serviceConfig:
            raise ValueError(f"Service '{serviceName}' not found in configuration")
        apiKey = serviceConfig['api']
        if not apiKey:
            raise ValueError(f"API key not configured for service '{serviceName}'")
        baseUrl = serviceConfig['url'] or None
        return OpenAI(api_key=apiKey, base_url=baseUrl)


    def processPrompt(self, promptName: str, serviceName: str,
                      selectedText: str = "", pdfFilePath: str = "",
                      inquiryResponse: str = "") -> Dict[str, Any]:
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
        promptConfig = self.configManager.getPromptByName(promptName)
        if not promptConfig:
            raise ValueError(f"Prompt '{promptName}' not found in configuration")
        attachmentType = promptConfig['attachment']
        client = self.createClient(serviceName)
        serviceConfig = self.configManager.getServiceByName(serviceName)
        if not serviceConfig:
            raise ValueError(f"Service '{serviceName}' not found in configuration")
        promptFooter = self.configManager.get('promptFooter')
        result = {'client': client, 'model': serviceConfig['model']}
        if attachmentType == 'selection':
            fullPrompt = f"{promptConfig['user-prompt']}\\n{selectedText}{promptFooter}"
            result['prompt'] = fullPrompt
        elif attachmentType == 'pdf':
            fullPrompt = f"{promptConfig['user-prompt']}{promptFooter}\\n"
            result['prompt'] = fullPrompt
            result['fileName'] = pdfFilePath
        elif attachmentType == 'inquiry':
            inquiryText = promptConfig['user-prompt'].split('|')[1]
            processedPrompt = promptConfig['user-prompt'].replace(f'|{inquiryText}|', inquiryResponse)
            fullPrompt = f"{processedPrompt}\\n\\n{selectedText}\\n{promptFooter}"
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
