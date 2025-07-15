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


    def processSelectionPrompt(self, promptName: str, serviceName: str,
                               selectedText: str) -> Dict[str, Any]:
        """Process a selection-based prompt.

        Args:
            promptName: Name of the prompt to use.
            serviceName: Name of the service to use.
            selectedText: Selected text from the editor.

        Returns:
            Dictionary with processing parameters for the worker.

        Raises:
            ValueError: If prompt or service is not found.
        """
        promptConfig = self.configManager.getPromptByName(promptName)
        if not promptConfig:
            raise ValueError(f"Prompt '{promptName}' not found in configuration")
        if promptConfig['attachment'] != 'selection':
            raise ValueError(f"Prompt '{promptName}' is not a selection prompt")
        client = self.createClient(serviceName)
        serviceConfig = self.configManager.getServiceByName(serviceName)
        promptFooter = self.configManager.get('promptFooter')
        fullPrompt = f"{promptConfig['user-prompt']}\\n{selectedText}{promptFooter}"
        return {
            'client': client,
            'model': serviceConfig['model'],
            'prompt': fullPrompt
        }


    def processPdfPrompt(self, promptName: str, serviceName: str, pdfFilePath: str) -> Dict[str, Any]:
        """Process a PDF-based prompt.

        Args:
            promptName: Name of the prompt to use.
            serviceName: Name of the service to use.
            pdfFilePath: Path to the PDF file.

        Returns:
            Dictionary with processing parameters for the worker.

        Raises:
            ValueError: If prompt or service is not found.
        """
        promptConfig = self.configManager.getPromptByName(promptName)
        if not promptConfig:
            raise ValueError(f"Prompt '{promptName}' not found in configuration")
        if promptConfig['attachment'] != 'pdf':
            raise ValueError(f"Prompt '{promptName}' is not a PDF prompt")
        client = self.createClient(serviceName)
        serviceConfig = self.configManager.getServiceByName(serviceName)
        promptFooter = self.configManager.get('promptFooter')
        fullPrompt = f"{promptConfig['user-prompt']}{promptFooter}\\n"
        return {
            'client': client,
            'model': serviceConfig['model'],
            'prompt': fullPrompt,
            'fileName': pdfFilePath
        }


    def processInquiryPrompt(self, promptName: str, serviceName: str,
                             selectedText: str, inquiryResponse: str) -> Dict[str, Any]:
        """Process an inquiry-based prompt.

        Args:
            promptName: Name of the prompt to use.
            serviceName: Name of the service to use.
            selectedText: Selected text from the editor.
            inquiryResponse: User's response to the inquiry.

        Returns:
            Dictionary with processing parameters for the worker.

        Raises:
            ValueError: If prompt or service is not found.
        """
        promptConfig = self.configManager.getPromptByName(promptName)
        if not promptConfig:
            raise ValueError(f"Prompt '{promptName}' not found in configuration")
        if promptConfig['attachment'] != 'inquiry':
            raise ValueError(f"Prompt '{promptName}' is not an inquiry prompt")
        client = self.createClient(serviceName)
        serviceConfig = self.configManager.getServiceByName(serviceName)
        promptFooter = self.configManager.get('promptFooter')
        # Extract inquiry text from the prompt
        inquiryText = promptConfig['user-prompt'].split('|')[1]
        # Replace the inquiry placeholder with the user's response
        processedPrompt = promptConfig['user-prompt'].replace(f'|{inquiryText}|', inquiryResponse)
        fullPrompt = f"{processedPrompt}\\n\\n{selectedText}\\n{promptFooter}"
        return {
            'client': client,
            'model': serviceConfig['model'],
            'prompt': fullPrompt
        }


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
            return promptConfig['user-prompt'].split('|')[1]
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
            content = content.split('\\n', 1)[-1].strip()
        return content


    def formatResponseForEditor(self, content: str) -> str:
        """Format the processed content for insertion into the editor.

        Args:
            content: Processed content from the LLM.

        Returns:
            Formatted content ready for editor insertion.
        """
        header = self.configManager.get('header')
        footer = self.configManager.get('footer')
        return f'{header}\\n{content}{footer}\\n'