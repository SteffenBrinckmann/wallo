"""Conversation widget containing all exchanges/turns and their operations."""
from typing import Any, Callable
from PySide6.QtCore import Qt, Signal  # pylint: disable=no-name-in-module
from PySide6.QtGui import QKeyEvent  # pylint: disable=no-name-in-module
from PySide6.QtWidgets import QScrollArea, QVBoxLayout, QWidget  # pylint: disable=no-name-in-module
from .configManager import ConfigurationManager
from .exchange import Exchange
from .llmProcessor import LLMProcessor
from .misc import HELP_TEXT
from .walloFiles import ExchangeData


class Conversation(QScrollArea):
    """Own the ordered exchanges that form one WALLO document."""
    changed = Signal()

    def __init__(self, configManager: ConfigurationManager, llmProcessor: LLMProcessor,
                 runWorker: Callable[[str, dict[str, Any]], None], exchangesData: list[ExchangeData],
                 beginner: bool) -> None:
        """Create the conversation and its exchanges.

        Args:
            configManager: Shared application configuration.
            llmProcessor: Shared prompt and response processor.
            runWorker: Callback for chat and capability work.
            exchangesData: Recovered exchange text in document order.
            beginner: Whether to show introductory help in a new document.
        """
        super().__init__()
        self.configManager = configManager
        self.llmProcessor = llmProcessor
        self._runWorker = runWorker
        container = QWidget(self)
        self.mainLayout = QVBoxLayout(container)
        self.mainLayout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.setWidgetResizable(True)
        self.setWidget(container)
        self.exchanges: list[Exchange] = []
        self.replaceExchanges(exchangesData)
        if beginner and not exchangesData:
            self.exchanges[0].text1.setMarkdown(HELP_TEXT)


    def runWorker(self, workType: str, work: dict[str, Any]) -> None:
        """Forward work requested by an exchange to the application.

        Args:
            workType: Kind of worker operation requested.
            work: Inputs required by the operation.
        """
        self._runWorker(workType, work)


    def exchangeData(self) -> list[ExchangeData]:
        """Return persisted text for every exchange/turn.

        Returns:
            Ordered exchange data for document persistence.
        """
        return [{'text1': exchange.text1.toPlainText(), 'text2': exchange.text2.toPlainText()}
                for exchange in self.exchanges]


    def content(self) -> str:
        """Return all exchanges as exportable Markdown.

        Returns:
            Concatenated textual representation of the conversation.
        """
        return ''.join(str(exchange) for exchange in self.exchanges)


    def layoutExchanges(self) -> None:
        """Put all exchanges into the conversation layout."""
        while self.mainLayout.count():
            item = self.mainLayout.takeAt(0)
            widget = item.widget() if item is not None else None
            if widget is not None:
                widget.setParent(None)
        for exchange in self.exchanges:
            self.mainLayout.addWidget(exchange)
        self.mainLayout.addStretch(2)


    def changeActive(self) -> None:
        """Update button visibility for every exchange."""
        for exchange in self.exchanges:
            if exchange.btnState == 'waiting':
                exchange.showButtons()
            else:
                exchange.hideButtons()


    def addExchanges(self, uuid: str, texts: list[str]) -> None:
        """Insert exchanges after an existing exchange.

        Args:
            uuid: Identifier of the exchange after which to insert.
            texts: Initial task-history text for each new exchange.
        """
        insertPos = [exchange.uuid for exchange in self.exchanges].index(uuid) + 1
        newExchanges = [Exchange(self, text) for text in texts]
        for exchange in newExchanges:
            self._connectExchange(exchange)
        self.exchanges[insertPos:insertPos] = newExchanges
        self.layoutExchanges()
        self.changed.emit()


    def deleteExchange(self, uuid: str) -> None:
        """Delete one exchange from the conversation.

        Args:
            uuid: Identifier of the exchange to delete.
        """
        idx = [exchange.uuid for exchange in self.exchanges].index(uuid)
        self.exchanges[idx].deleteLater()
        del self.exchanges[idx]
        self.changed.emit()


    def replaceExchanges(self, exchangesData: list[ExchangeData]) -> None:
        """Replace the conversation with persisted exchange data.

        Args:
            exchangesData: Ordered exchanges to display.
        """
        for exchange in self.exchanges:
            exchange.deleteLater()
        self.exchanges = []
        for exchangeData in exchangesData:
            exchange = Exchange(self, exchangeData['text1'])
            if exchangeData['text2']:
                exchange.text2.setPlainText(exchangeData['text2'])
                exchange.text2.show()
            self.exchanges.append(exchange)
        if not self.exchanges:
            self.exchanges = [Exchange(self) for _ in range(2)]
        for exchange in self.exchanges:
            self._connectExchange(exchange)
        self.layoutExchanges()
        self.exchanges[0].showButtons()


    def setReply(self, content: str, senderID: str, workType: str) -> None:
        """Deliver worker output to its originating exchange.

        Args:
            content: Processed worker output.
            senderID: Identifier of the originating exchange.
            workType: Worker operation that produced the output.
        """
        for exchange in self.exchanges:
            exchange.setReply(content, senderID, workType)


    def setSpellcheck(self, enabled: bool) -> None:
        """Enable or disable spell checking for every editor.

        Args:
            enabled: Desired spell-checking state.
        """
        for exchange in self.exchanges:
            exchange.text1.setSpellCheckEnabled(enabled)
            exchange.text2.setSpellCheckEnabled(enabled)


    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Move between exchanges for Ctrl+PageUp and Ctrl+PageDown.

        Args:
            event: Key event received by the conversation.
        """
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            if event.key() == Qt.Key.Key_PageDown:
                self._moveActiveExchange(1)
                return
            if event.key() == Qt.Key.Key_PageUp:
                self._moveActiveExchange(-1)
                return
        super().keyPressEvent(event)


    def _connectExchange(self, exchange: Exchange) -> None:
        """Connect an exchange to recovery persistence.

        Args:
            exchange: Exchange whose text changes must be persisted.
        """
        exchange.text1.textChanged.connect(self.changed.emit)
        exchange.text2.textChanged.connect(self.changed.emit)


    def _moveActiveExchange(self, step: int) -> None:
        """Move keyboard focus by a relative exchange offset.

        Args:
            step: Signed number of exchanges to move.
        """
        activeIdx = next((idx for idx, exchange in enumerate(self.exchanges)
                          if exchange.btnState == 'show'), None)
        if activeIdx is None or not 0 <= activeIdx + step < len(self.exchanges):
            return
        self.exchanges[activeIdx].hideButtons()
        self.exchanges[activeIdx + step].showButtons()
        self.exchanges[activeIdx + step].focusForTyping()
