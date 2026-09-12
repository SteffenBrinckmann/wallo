"""Main window for the Wallo application, providing a text editor with LLM assistance."""

import sys
import json
from functools import partial
from pathlib import Path
from typing import Any
import pypandoc
import qtawesome as qta
from PySide6.QtCore import QThread, Qt, Signal  # pylint: disable=no-name-in-module
from PySide6.QtGui import QAction, QKeySequence, QKeyEvent, QCloseEvent  # pylint: disable=no-name-in-module
from PySide6.QtWidgets import (QApplication,  QComboBox, QFileDialog, QMainWindow, QMessageBox, QScrollArea, # pylint: disable=no-name-in-module
                               QToolBar, QVBoxLayout, QWidget)

from .configMain import ConfigurationWidget
from .configManager import ConfigurationManager
from .exchange import Exchange
from .llmProcessor import LLMProcessor
from .misc import invertIcon, HELP_TEXT
from .worker import Worker
from .services.service import Service, createService

class Wallo(QMainWindow):
    """Main window for the Wallo application, providing a text editor with LLM assistance."""
    serviceFinished = Signal(str, str, str)
    serviceError = Signal(str, str, str)
    serviceModels = Signal(list)
    serviceModelError = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.configManager = ConfigurationManager()
        self.recoveryPath = Path.home() / '.wallo-recovery.json'
        self.beginner = self.configManager.get('startCounts') > 0
        if self.beginner:
            self.configManager.updateConfig({'startCounts': self.configManager.get('startCounts') - 1})
        self.llmProcessor = LLMProcessor(self.configManager)
        self.configWidget: ConfigurationWidget | None = None
        self.activeThreads: list[QThread] = []
        self.activeWorkers: list[Worker] = []
        self.spellcheck = True
        self.serviceCB = QComboBox()
        self.profileCB = QComboBox()
        self.modelsCB = QComboBox()
        self.activeService: Service | None = None
        self.serviceFinished.connect(self.onWorkerFinished)
        self.serviceError.connect(self.onWorkerError)
        self.serviceModels.connect(self._onServiceModels)
        self.serviceModelError.connect(self._onServiceModelError)

        # GUI
        self.setWindowTitle('WALLO - Writing Assistance by Large Language mOdel')
        container = QWidget(self)
        self.mainLayout = QVBoxLayout(container)
        self.mainLayout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scrollArea = QScrollArea(self)
        scrollArea.setWidgetResizable(True)
        scrollArea.setWidget(container)
        self.setCentralWidget(scrollArea)

        # Setup exchanges
        recoveredExchanges = self._loadRecovery()
        # WALLO documents are ordered exchanges, also called conversation turns.
        self.exchanges: list[Exchange] = []
        if recoveredExchanges:
            for recoveredExchange in recoveredExchanges:
                exchange = Exchange(self, recoveredExchange['text1'])
                if recoveredExchange['text2']:
                    exchange.text2.setPlainText(recoveredExchange['text2'])
                    exchange.text2.show()
                self.exchanges.append(exchange)
        else:
            self.exchanges = [Exchange(self) for _ in range(2)]
        for exchange in self.exchanges:
            self._connectRecovery(exchange)
        self.layoutExchanges()
        self.exchanges[0].showButtons()
        if self.beginner and not recoveredExchanges:
            self.exchanges[0].text1.setMarkdown(HELP_TEXT)

        self.toolbar = QToolBar('Main')
        self.addToolBar(self.toolbar)
        self.spellIcon = qta.icon('fa5s.spell-check')
        self.spellIconInverted = invertIcon(self.spellIcon)
        self.spellcheckAction = QAction('', self, icon=self.spellIconInverted, checkable=True,
                                        toolTip='Toggle spellchecker')
        self.spellcheckAction.setChecked(self.spellcheck)
        self.spellcheckAction.triggered.connect(self.toggleSpellcheck)
        self.toolbar.addAction(self.spellcheckAction)
        self.toolbar.addWidget(self._toolbarSpacer())
        saveAction = QAction('', self, icon=qta.icon('fa5.save'), toolTip='Save as docx or markdown')
        saveAction.triggered.connect(lambda: self.saveToFile('text'))
        self.toolbar.addAction(saveAction)
        ttsAction = QAction('', self, icon=qta.icon('fa5.file-audio'), toolTip='Save to mp3 file')
        ttsAction.triggered.connect(lambda: self.saveToFile('tts'))
        self.toolbar.addAction(ttsAction)
        self.toolbar.addWidget(self._toolbarSpacer())
        self.toolbar.addWidget(self.profileCB)
        self.profileCB.activated.connect(lambda: self.onConfigChanged('profile'))
        self.toolbar.addSeparator()
        self.toolbar.addWidget(self.serviceCB)
        self.serviceCB.activated.connect(lambda: self.onConfigChanged('service'))
        self.toolbar.addWidget(self.modelsCB)
        self.modelsCB.activated.connect(lambda: self.onConfigChanged('model'))
        self.toolbar.addWidget(self._toolbarSpacer())
        ragAction = QAction('', self, icon=qta.icon('mdi.database-plus'), toolTip='Add files to knowledge base')
        ragAction.triggered.connect(self.addRagSources)
        self.toolbar.addAction(ragAction)
        self.toolbar.addWidget(self._toolbarSpacer())
        self.agentIcon = qta.icon('fa5s.robot')
        self.agentIconInverted = invertIcon(self.agentIcon)
        self.agentUseAction = QAction('', self, icon=self.agentIcon, toolTip='Allow to use LLM Agents')
        self.agentUseAction.triggered.connect(self.toggleAgentsUse)
        self.toolbar.addAction(self.agentUseAction)
        self.pastaUseIcon = qta.icon('mdi.pasta')
        self.pastaUseIconInverted = invertIcon(self.pastaUseIcon)
        self.pastaUseAction = QAction('', self, icon=self.pastaUseIcon, toolTip='Link and use PASTA-ELN database')
        self.pastaUseAction.triggered.connect(self.linkPastaELN)
        self.toolbar.addAction(self.pastaUseAction)
        self.toolbar.addWidget(self._toolbarSpacer())
        configAction = QAction('', self, icon=qta.icon('fa5s.cog'), toolTip='Configuration',
                               shortcut=QKeySequence('Ctrl+0'))
        configAction.triggered.connect(self.showConfiguration)
        self.toolbar.addAction(configAction)
        self.onConfigChanged()


    def _toolbarSpacer(self, width: int = 20) -> QWidget:
        spacer = QWidget()
        spacer.setFixedWidth(width)
        return spacer


    def _loadRecovery(self) -> list[dict[str, str]]:
        """Load the text-only exchanges saved after an interrupted session."""
        try:
            with open(self.recoveryPath, 'r', encoding='utf-8') as recoveryFile:
                recoveredExchanges = json.load(recoveryFile)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return []
        if not isinstance(recoveredExchanges, list):
            return []
        for recoveredExchange in recoveredExchanges:
            if not isinstance(recoveredExchange, dict) or 'text1' not in recoveredExchange or \
                    'text2' not in recoveredExchange or not isinstance(recoveredExchange['text1'], str) or \
                    not isinstance(recoveredExchange['text2'], str):
                return []
        return recoveredExchanges


    def _connectRecovery(self, exchange: Exchange) -> None:
        """Save a recovery draft whenever exchange text changes."""
        exchange.text1.textChanged.connect(self.saveRecovery)
        exchange.text2.textChanged.connect(self.saveRecovery)


    def saveRecovery(self) -> None:
        """Atomically save the text in every exchange for crash recovery."""
        recoveredExchanges = [{'text1': exchange.text1.toPlainText(), 'text2': exchange.text2.toPlainText()}
                              for exchange in self.exchanges]
        tempPath = self.recoveryPath.with_name(self.recoveryPath.name + '.tmp')
        try:
            with open(tempPath, 'w', encoding='utf-8') as recoveryFile:
                json.dump(recoveredExchanges, recoveryFile)
            tempPath.replace(self.recoveryPath)
        except OSError:
            pass


    def layoutExchanges(self) -> None:
        """Put the exchanges into the main layout."""
        while self.mainLayout.count():
            item = self.mainLayout.takeAt(0)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
        for exchange in self.exchanges:
            self.mainLayout.addWidget(exchange)
        self.mainLayout.addStretch(2)


    def changeActive(self) -> None:
        """For all exchanges: change the showing of the buttons."""
        for exchange in self.exchanges:
            if exchange.btnState == 'waiting':
                exchange.showButtons()
            else:
                exchange.hideButtons()


    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle key press events.

        Args:
            event (QKeyEvent): The key press event.
        """
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            if event.key() == Qt.Key.Key_PageDown:
                self._moveActiveExchange(1)
                return
            if event.key() == Qt.Key.Key_PageUp:
                self._moveActiveExchange(-1)
                return
        super().keyPressEvent(event)

    def _moveActiveExchange(self, step: int) -> None:
        activeIdx = None
        for idx, exchange in enumerate(self.exchanges):
            if exchange.btnState == 'show':
                activeIdx = idx
        if activeIdx is None:
            return
        newIdx = activeIdx + step
        if not 0 <= newIdx < len(self.exchanges):
            return
        self.exchanges[activeIdx].hideButtons()
        self.exchanges[newIdx].showButtons()
        self.exchanges[newIdx].focusForTyping()




    def addExchanges(self, uuid: str, texts: list[str]) -> None:
        """Add exchanges.

        Args:
          uuid (str): The UUID of the exchange.
          texts (list[str]): texts to be added into new exchanges
        """
        idx = [exchange.uuid for exchange in self.exchanges].index(uuid)
        insertPos = idx + 1
        newExchanges = [Exchange(self, text) for text in texts]
        for exchange in newExchanges:
            self._connectRecovery(exchange)
        self.exchanges[insertPos:insertPos] = newExchanges
        self.layoutExchanges()
        self.saveRecovery()


    def deleteExchange(self, uuid: str) -> None:
        """Add exchanges.

        Args:
          uuid (str): The UUID of the exchange.
        """
        idx = [exchange.uuid for exchange in self.exchanges].index(uuid)
        self.exchanges[idx].deleteLater()
        del self.exchanges[idx]
        self.saveRecovery()


    def saveToFile(self, dType: str) -> None:
        """Save the content of the editor to file.

        Args:
            dType (str): The type of file to save (e.g., 'text' or 'tts').
        """
        filterText = 'Word Files (*.docx);;Markdown Files (*.md)' if dType == 'text' else 'Audio Files (*.mp3)'
        filename, _ = QFileDialog.getSaveFileName(self, 'Save to File', str(Path.home()), filterText)
        if not filename:
            return
        content = ''.join(str(exchange) for exchange in self.exchanges)
        reply = QMessageBox.question(self, 'Structure content?',
                'Should I structure the content by adding headings and creating bullet points when appropriate?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            content = self.llmProcessor.structureContent(content)
        if dType == 'text':
            if filename.lower().endswith('.docx'):
                pypandoc.convert_text(content, 'docx', format='md', outputfile=filename, extra_args=['--standalone'])
                return
            with open(filename, 'w', encoding='utf-8') as fh:
                fh.write(content)
            return
        possOpenAI = self.configManager.getOpenAiServices()
        if not possOpenAI:
            QMessageBox.critical(None, 'Configuration error', 'No OpenAI services configured')
            return
        apiKey = self.configManager.getServiceByName(possOpenAI[0])['api']
        self.runWorker('tts', {'apiKey': apiKey, 'filePaths': filename, 'content': content, 'senderID': 'tts'})


    def runWorker(self, workType: str, work: dict[str, Any]) -> None:
        """Run a worker thread to perform the specified work -> keep GUI responsive.

        Args:
            workType (str): The type of work to be performed (e.g., 'chatAPI', 'pdfExtraction').
            work (dict): The work parameters, such as client, model, prompt, and fileName.
        """
        # A chat request completes the active exchange/turn.
        if workType == 'chatAPI':
            if self.activeService is None:
                self.onWorkerError('No active service', work['senderID'], workType)
                return
            senderID = work['senderID']
            self.activeService.runChat(work,
                lambda content: self.serviceFinished.emit(content, senderID, workType),
                lambda errorMsg: self.serviceError.emit(errorMsg, senderID, workType))
            return
        self.runWorkerLangchain(workType, work)


    def runWorkerLangchain(self, workType: str, work: dict[str, Any]) -> None:
        """Run existing worker path for LangChain/OpenAI operations."""
        thread = QThread()
        worker = Worker(workType, work)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self.onWorkerFinished)
        worker.error.connect(self.onWorkerError)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(partial(self._onThreadFinished, thread, worker))
        thread.finished.connect(thread.deleteLater)
        self.activeThreads.append(thread)
        self.activeWorkers.append(worker)
        thread.start()


    def closeEvent(self, event: QCloseEvent) -> None:
        """Close the app and clean up active service resources.

        Args:
            event: Qt close event to pass to the base window.
        """
        if self.activeService is not None:
            self.activeService.stop()
        super().closeEvent(event)
        if event.isAccepted():
            try:
                self.recoveryPath.unlink()
            except FileNotFoundError:
                pass
            except OSError:
                pass


    def _loadServiceModels(self) -> None:
        """Load models from the active service."""
        self.modelsCB.clear()
        self.modelsCB.setEnabled(False)
        if self.activeService is not None:
            self.activeService.getModels(self.serviceModels.emit, self.serviceModelError.emit)


    def _onServiceModels(self, models: list[str]) -> None:
        """Populate the model selector with service-reported models.

        Args:
            models: Model names reported by the active service.
        """
        self.modelsCB.clear()
        self.modelsCB.addItems(models)
        self.modelsCB.setEnabled(bool(models))
        if models:
            self.configManager.set('model', models[0])


    def _onServiceModelError(self, errorMsg: str) -> None:
        """Show an error if the active service cannot report models.

        Args:
            errorMsg: Error returned by the active service.
        """
        QMessageBox.critical(self, 'Service Error', errorMsg)


    def _onThreadFinished(self, thread: QThread, worker: Worker) -> None:
        """Drop finished thread/worker references to allow cleanup."""
        if thread in self.activeThreads:
            self.activeThreads.remove(thread)
        if worker in self.activeWorkers:
            self.activeWorkers.remove(worker)


    def _activateService(self) -> None:
        """Replace the active service and reset its chat state."""
        if self.activeService is not None:
            self.activeService.stop()
        # Switching service starts a fresh conversation rather than sharing turns across backends.
        self.llmProcessor.resetChat()
        self.activeService = createService(self.configManager)
        self._loadServiceModels()


    def onWorkerFinished(self, content: str, senderID: str, workType: str) -> None:
        """Handle the completion of the LLM worker.

        Args:
            content (str): The content generated by the LLM worker.
            senderID (str): The sender ID of the exchange
            workType (str): The type of work performed (e.g., 'chatAPI', 'pdfExtraction')
        """
        processContent = self.llmProcessor.processLLMResponse(content)
        for exchange in self.exchanges:
            exchange.setReply(processContent, senderID, workType)


    def onWorkerError(self, errorMsg: str, senderID: str, workType: str = '') -> None:
        """Handle errors from the LLM worker.

        Args:
            errorMsg (str): The error message from the worker.
            senderID (str): The sender ID of the exchange
            workType (str): The type of work performed (e.g., 'chatAPI', 'pdfExtraction')
        """
        info = f'{errorMsg} by senderID {senderID}'
        QMessageBox.critical(self, 'Worker Error', f'{info} ({workType})' if workType else info)


    def toggleSpellcheck(self) -> None:
        """Toggle spell checking on or off."""
        self.spellcheck = not self.spellcheck
        for exchange in self.exchanges:
            exchange.text1.setSpellCheckEnabled(self.spellcheck)
            exchange.text2.setSpellCheckEnabled(self.spellcheck)
        self.spellcheckAction.setIcon(self.spellIconInverted if self.spellcheck else self.spellIcon)


    def toggleAgentsUse(self) -> None:
        """Toggle agent use on or off."""
        self.llmProcessor.agents.useAgents = not self.llmProcessor.agents.useAgents
        self.agentUseAction.setIcon(self.agentIconInverted if self.llmProcessor.agents.useAgents else self.agentIcon)


    def linkPastaELN(self) -> None:
        """Toggle PASTA-ELN use on or off."""
        filename, _ = QFileDialog.getOpenFileName(self, 'Select a PASTA-ELN database', str(Path.home()),
                                                  'SQLite Files (*.db)')
        if filename:
            self.llmProcessor.agents.usePastaEln = filename
            self.pastaUseAction.setIcon(self.pastaUseIconInverted)


    def addRagSources(self) -> None:
        """Open a file or folder dialog to add sources to the RAG knowledge base."""
        filePaths, _ = QFileDialog.getOpenFileNames(self, 'Select files to add to knowledge base', '', 'All Files (*)')
        if not filePaths:
            if directory := QFileDialog.getExistingDirectory(self, 'Select folder to add to knowledge base'):
                filePaths = [directory]
        if not filePaths:
            return
        self.runWorker('ingestRAG', {'runnable': self.llmProcessor.ragIndexer, 'filePaths': filePaths,
                                     'senderID': 'ingestRAG'})


    def showConfiguration(self) -> None:
        """Show the configuration widget."""
        if self.configWidget is None:
            self.configWidget = ConfigurationWidget(self.configManager)
            self.configWidget.configChanged.connect(lambda: self.onConfigChanged('reread'))
        self.configWidget.show()
        self.configWidget.raise_()
        self.configWidget.activateWindow()


    def onConfigChanged(self, dType:str='initialize') -> None:
        """Apply a configuration or toolbar selection change.

        Args:
            dType: Changed configuration category or initialization marker.
        """
        if dType=='reread':
            self.configManager.loadConfig()
            dType = 'initialize'
        if dType == 'initialize':
            self.profileCB.clear()
            self.profileCB.addItems(self.configManager.get('profiles'))
            currentProfile = self.configManager.get('profiles')[0]
            self.configManager.set('profile', currentProfile)

            self.serviceCB.clear()
            services = self.configManager.get('services')
            self.serviceCB.addItems(list(services.keys()))
            currentService = list(services.keys())[0]
            self.configManager.set('service', currentService)

            del services
            self._activateService()
        if dType=='profile':
            self.configManager.set(dType, self.profileCB.currentText())
        if dType=='service':
            currentService = self.serviceCB.currentText()
            self.configManager.set(dType, currentService)
            self._activateService()
        if dType=='model':
            self.configManager.set(dType, self.modelsCB.currentText())


if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = Wallo()
    win.resize(1024, 800)
    win.show()
    sys.exit(app.exec())
