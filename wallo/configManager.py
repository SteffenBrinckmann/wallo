"""Configuration management for the Wallo application."""
import json
from pathlib import Path
from typing import Any, Optional
from jsonschema import validate, ValidationError

DEFAULT_CONFIGURATION = {
    'prompts': [
        {
            'name': 'Make the text professional',
            'user-prompt': 'Can you make the following paragraph more professional and polished:',
            'attachment':  'selection'
        },
        {
            'name': 'summarize the paper',
            'user-prompt': 'Can you summarize the following paper:',
            'attachment':  'pdf'
        }
    ],
    'system-prompts': [
        {
            'name': 'Default',
            'system-prompt': 'You are a helpful assistant.',
        }
    ],
    'services': {
        'openAI': {'url':'', 'api':None, 'model': 'gpt-4o', 'type': 'openAI'}
    },
  'dictionary': 'en_US',
  'startCounts': 4
}


class ConfigurationManager:
    """Handles configuration loading, validation, and management."""

    def __init__(self, configFile: Optional[Path] = None) -> None:
        """Initialize the configuration manager.

        Args:
            configFile: Path to the configuration file. If None, uses default location.
        """
        self.configFile = configFile or Path.home() / '.wallo.json'
        self._config: dict[str, Any] = {}
        self.loadConfig()


    def loadConfig(self) -> None:
        """Load configuration from file, creating default if it doesn't exist."""
        if not self.configFile.is_file():
            # Create default configuration file
            try:
                with open(self.configFile, 'w', encoding='utf-8') as confFile:
                    json.dump(DEFAULT_CONFIGURATION, confFile, indent=2)
            except OSError as e:
                raise ValueError(f"Error creating default configuration file: {e}") from e
        try:
            with open(self.configFile, encoding='utf-8') as confFile:
                self._config = json.load(confFile)
        except (json.JSONDecodeError, OSError) as e:
            raise ValueError(f"Error loading configuration file: {e}") from e
        self.validateConfig()


    def validateConfig(self) -> None:
        """Validate configuration file format and required fields.

        If jsonschema is available, use the bundled schema for validation and
        provide detailed errors. Otherwise fall back to lightweight checks.
        """
        schemaPath = Path(__file__).parent / 'configSchema.json'
        if schemaPath.is_file():
            with open(schemaPath, encoding='utf-8') as s:
                schema = json.load(s)
            try:
                validate(instance=self._config, schema=schema)
                return
            except ValidationError as e:
                path = '/'.join(map(str, e.path)) if e.path else '<root>'
                raise ValueError(f"Configuration validation error at {path}: {e.message}") from e


    def get(self, info:str) -> Any:
        """Get configuration value by key."""
        if info not in ['prompts', 'system-prompts','services','dictionary','startCounts']:
            raise ValueError(f"Invalid info type '{info}' requested")
        if info in ['prompts', 'system-prompts', 'services']:
            return self._config[info]
        if info in ['dictionary','startCounts']:
            return self._config.get(info, DEFAULT_CONFIGURATION[info])
        return []


    def getPromptByName(self, name: str) -> dict[str, Any]:
        """Get a specific prompt by name."""
        prompts = self._config['prompts']
        for prompt in prompts:
            if prompt['name'] == name:
                return prompt  # type: ignore
        default = {'name': 'default', 'user-prompt': '', 'inquiry': False}
        return default


    def getServiceByName(self, name: str) -> dict[str, Any]:
        """Get a specific service by name."""
        services = self._config['services']
        return services[name]  # type: ignore


    def getOpenAiServices(self) -> list[str]:
        """ Get all services that are of type 'openai'
        Returns:
            List of service names
        """
        services = self._config['services']
        return [name for name, service in services.items() if service['type'] == 'openAI' and service['url']=='']


    def saveConfig(self) -> None:
        """Save current configuration to file."""
        try:
            with open(self.configFile, 'w', encoding='utf-8') as confFile:
                json.dump(self._config, confFile, indent=2)
        except OSError as e:
            raise ValueError(f"Error saving configuration file: {e}") from e


    def updateConfig(self, updates: dict[str, Any]) -> None:
        """Update configuration with new values."""
        self._config.update(updates)
        self.validateConfig()
        self.saveConfig()
