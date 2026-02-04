"""Main window for the Wallo application, providing a text editor with LLM assistance."""

import sys
from functools import partial
from pathlib import Path
from typing import Any
import pypandoc
import qtawesome as qta
from PySide6.QtCore import QThread, Qt  # pylint: disable=no-name-in-module
from PySide6.QtGui import QAction, QKeySequence, QKeyEvent  # pylint: disable=no-name-in-module
from PySide6.QtWidgets import (QApplication,  QComboBox, QFileDialog, QMainWindow, QMessageBox, QScrollArea, # pylint: disable=no-name-in-module
                               QToolBar, QVBoxLayout, QWidget)
from .configMain import ConfigurationWidget
from .configManager import ConfigurationManager
from .exchange import Exchange
from .llmProcessor import LLMProcessor
from .misc import invertIcon, HELP_TEXT
from .worker import Worker


class Wallo(QMainWindow):
    """Main window for the Wallo application, providing a text editor with LLM assistance."""
    def __init__(self) -> None:
        super().__init__()
        self.configManager = ConfigurationManager()
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
        self.exchanges: list[Exchange] = [Exchange(self) for _ in range(2)]
        self.layoutExchanges()
        self.exchanges[0].showButtons()
        if self.beginner:
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


    def layoutExchanges(self) -> None:
        """Put the exchanges into the main layout."""
        while self.mainLayout.count():
            widget = self.mainLayout.takeAt(0).widget()
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
        self.exchanges[insertPos:insertPos] = [Exchange(self, text) for text in texts]
        self.layoutExchanges()


    def deleteExchange(self, uuid: str) -> None:
        """Add exchanges.

        Args:
          uuid (str): The UUID of the exchange.
        """
        idx = [exchange.uuid for exchange in self.exchanges].index(uuid)
        self.exchanges[idx].deleteLater()
        del self.exchanges[idx]


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


    def _onThreadFinished(self, thread: QThread, worker: Worker) -> None:
        """Drop finished thread/worker references to allow cleanup."""
        if thread in self.activeThreads:
            self.activeThreads.remove(thread)
        if worker in self.activeWorkers:
            self.activeWorkers.remove(worker)


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


    def onWorkerError(self, errorMsg: str, senderID: str) -> None:
        """Handle errors from the LLM worker.

        Args:
            errorMsg (str): The error message from the worker.
            senderID (str): The sender ID of the exchange
        """
        QMessageBox.critical(self, 'Worker Error', f'{errorMsg} by senderID {senderID}')


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
            directory = QFileDialog.getExistingDirectory(self, 'Select folder to add to knowledge base')
            if directory:
                filePaths = [directory]
        if not filePaths:
            return
        self.runWorker('ingestRAG', {'runnable': self.llmProcessor.ragIndexer, 'filePaths': filePaths})


    def showConfiguration(self) -> None:
        """Show the configuration widget."""
        if self.configWidget is None:
            self.configWidget = ConfigurationWidget(self.configManager)
            self.configWidget.configChanged.connect(lambda: self.onConfigChanged('reread'))
        self.configWidget.show()
        self.configWidget.raise_()
        self.configWidget.activateWindow()


    def onConfigChanged(self, dType:str='initialize') -> None:
        """Handle configuration changes."""
        if dType=='reread':
            self.configManager.readConfig()
            dType = 'initialize'
        if dType=='initialize':
            self.profileCB.clear()
            self.profileCB.addItems(self.configManager.get('profiles'))
            currentProfile = self.configManager.get('profiles')[0]
            self.configManager.set('profile', currentProfile)

            self.serviceCB.clear()
            services = self.configManager.get('services')
            self.serviceCB.addItems(list(services.keys()))
            currentService = list(services.keys())[0]
            self.configManager.set('service', currentService)

            self.modelsCB.clear()
            self.modelsCB.addItems(list(services[currentService]['models'].keys()))
            currentModel = list(services[currentService]['models'].keys())[0]
            self.configManager.set('model', currentModel)
        if dType=='profile':
            self.configManager.set(dType, self.profileCB.currentText())
        if dType=='service':
            currentService = self.serviceCB.currentText()
            self.configManager.set(dType, currentService)
            self.modelsCB.clear()
            services = self.configManager.get('services')
            self.modelsCB.addItems(list(services[currentService]['models'].keys()))
            currentModel = list(services[currentService]['models'].keys())[0]
            self.configManager.set('model', currentModel)
        if dType=='model':
            self.configManager.set(dType, self.modelsCB.currentText())


if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = Wallo()
    win.resize(1024, 800)
    win.show()
    sys.exit(app.exec())
