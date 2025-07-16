"""Configuration management for the Wallo application."""
import json
from pathlib import Path
from typing import Dict, Any, Optional

DEFAULT_CONFIGURATION = {
    'prompts': [
        {
            'name': 'Professional',
            'description': 'Make the text professional',
            'user-prompt': 'Can you make the following paragraph more professional and polished:',
            'attachment':  'selection'
        },
        {
        "name": "summarize_paper",
        "description": "Summarize pdf after uploading it",
        "user-prompt": "Can you summarize the following paper:",
        "attachment":  "pdf"
        }
    ],
    'services': {
        'openAI': {'url':'', 'api':None, 'model': 'gpt-4o'}
    },
  "promptFooter": "\nPlease reply with the html formatted string only",
  "footer": f'\n{"-"*5} Start LLM generated {"-"*5}',
  "header": f'\n{"-"*5}  End LLM generated  {"-"*5}'
}


class ConfigurationManager:
    """Handles configuration loading, validation, and management."""

    def __init__(self, configFile: Optional[Path] = None) -> None:
        """Initialize the configuration manager.

        Args:
            configFile: Path to the configuration file. If None, uses default location.
        """
        self.configFile = configFile or Path.home() / '.wallo.json'
        self._config: Dict[str, Any] = {}
        self.loadConfig()


    def loadConfig(self) -> None:
        """Load configuration from file, creating default if it doesn't exist."""
        if not self.configFile.is_file():
            # Create default configuration file
            try:
                with open(self.configFile, 'w', encoding='utf-8') as confFile:
                    json.dump(DEFAULT_CONFIGURATION, confFile, indent=2)
            except IOError as e:
                raise ValueError(f"Error creating default configuration file: {e}") from e
        try:
            with open(self.configFile, 'r', encoding='utf-8') as confFile:
                self._config = json.load(confFile)
        except (json.JSONDecodeError, IOError) as e:
            raise ValueError(f"Error loading configuration file: {e}") from e
        self.validateConfig()


    def validateConfig(self) -> None:
        """Validate configuration file format and required fields."""
        requiredFields = ['prompts', 'services']
        for field in requiredFields:
            if field not in self._config:
                raise ValueError(f"Missing required field '{field}' in configuration")
        if not isinstance(self._config['prompts'], list):
            raise ValueError("'prompts' must be a list")
        if not isinstance(self._config['services'], dict):
            raise ValueError("'services' must be a dictionary")
        # Validate prompt structure
        for i, prompt in enumerate(self._config['prompts']):
            requiredPromptFields = ['name', 'description', 'user-prompt', 'attachment']
            for field in requiredPromptFields:
                if field not in prompt:
                    raise ValueError(f"Missing required field '{field}' in prompt {i}")
        # Validate service structure
        for serviceName, serviceConfig in self._config['services'].items():
            requiredServiceFields = ['url', 'api', 'model']
            for field in requiredServiceFields:
                if field not in serviceConfig:
                    raise ValueError(f"Missing required field '{field}' in service '{serviceName}'")


    def get(self, info:str) -> Any:
        """Get configuration value by key."""
        if info not in ['prompts', 'services', 'promptFooter', 'header', 'footer']:
            raise ValueError(f"Invalid info type '{info}' requested")
        if info in ['prompts', 'services']:
            return self._config[info]
        if info in ['promptFooter', 'header', 'footer']:
            return self._config.get(info, DEFAULT_CONFIGURATION[info])
        return []


    def getPromptByName(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a specific prompt by name."""
        prompts = self._config['prompts']
        for prompt in prompts:
            if prompt['name'] == name:
                return prompt  # type: ignore
        return None


    def getServiceByName(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a specific service by name."""
        services = self._config['services']
        return services.get(name)  # type: ignore


    def saveConfig(self) -> None:
        """Save current configuration to file."""
        try:
            with open(self.configFile, 'w', encoding='utf-8') as confFile:
                json.dump(self._config, confFile, indent=2)
        except IOError as e:
            raise ValueError(f"Error saving configuration file: {e}") from e


    def updateConfig(self, updates: Dict[str, Any]) -> None:
        """Update configuration with new values."""
        self._config.update(updates)
        self.validateConfig()
        self.saveConfig()
