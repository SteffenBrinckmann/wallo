"""Shared service interface and construction."""
from typing import Any, Callable, Protocol
from .acp.service import AcpService
from .api.service import ApiService
from .codex.service import CodexService
from ..configManager import ConfigurationManager


class Service(Protocol):
    """Common operations for a configured chat service."""

    def runChat(self, work: dict[str, Any], successCb: Callable[[str], None],
                errorCb: Callable[[str], None]) -> None:
        """Run one chat request for an exchange, also called a turn.

        Args:
            work: Prepared chat request inputs.
            successCb: Callback receiving generated text.
            errorCb: Callback receiving an error message.
        """

    def getModels(self, successCb: Callable[[list[str]], None], errorCb: Callable[[str], None]) -> None:
        """Return available models, if the service provides them.

        Args:
            successCb: Callback receiving model names.
            errorCb: Callback receiving an error message.
        """

    def stop(self) -> None:
        """Release resources owned by this service"""


def createService(configManager: ConfigurationManager) -> Service:
    """Create the currently selected chat service.

    Args:
        configManager: Source of the currently selected service configuration.
    Returns:
        Adapter implementing the selected chat service.
    """
    service = configManager.get('service')
    if service['type'] == 'api':
        return ApiService(configManager)
    if service['type'] == 'acp':
        return AcpService()
    if service['type'] == 'codex':
        return CodexService()
    raise ValueError(f"Unknown service type '{service['type']}'")
