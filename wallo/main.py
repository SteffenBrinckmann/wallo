"""Main window for the Wallo application, providing a text editor with LLM assistance."""

import sys
from functools import partial
from pathlib import Path
from typing import Any
import pypandoc
from PySide6.QtCore import QThread, Signal  # pylint: disable=no-name-in-module
from PySide6.QtGui import QCloseEvent  # pylint: disable=no-name-in-module
from PySide6.QtWidgets import QApplication, QFileDialog, QMainWindow, QMessageBox  # pylint: disable=no-name-in-module

from .configManager import ConfigurationManager
from .conversation import Conversation
from .llmProcessor import LLMProcessor
from .worker import Worker
from .services.service import Service, createService
from .toolbar import Toolbar
from .walloFiles import DocumentData, SelectionData, WalloFiles

# pylint: disable=too-many-statements
class Wallo(QMainWindow):
    """Main window for the Wallo application, providing a text editor with LLM assistance."""
    serviceFinished = Signal(str, str, str)
    serviceError = Signal(str, str, str)
    serviceModels = Signal(list)
    serviceModelError = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.configManager = ConfigurationManager()
        self.walloFiles = WalloFiles(Path.home() / '.wallo-recovery.json')
        self.beginner = self.configManager.get('startCounts') > 0
        if self.beginner:
            self.configManager.updateConfig({'startCounts': self.configManager.get('startCounts') - 1})
        self.llmProcessor = LLMProcessor(self.configManager)
        self.activeThreads: list[QThread] = []
        self.activeWorkers: list[Worker] = []
        self.activeService: Service | None = None
        self.serviceFinished.connect(self.onWorkerFinished)
        self.serviceError.connect(self.onWorkerError)

        # GUI
        self.setWindowTitle('WALLO - Writing Assistance by Large Language mOdel')
        recoveredDocument = self.walloFiles.loadRecovery()
        recoveredExchanges = recoveredDocument['exchanges'] if recoveredDocument is not None else []
        self.conversation = Conversation(self.configManager, self.llmProcessor, self.runWorker,
                                         recoveredExchanges, self.beginner)
        self.conversation.changed.connect(self.saveRecovery)
        self.setCentralWidget(self.conversation)

        self.toolbar = Toolbar(self)
        self.addToolBar(self.toolbar)
        self.serviceModels.connect(self.toolbar.setModels)
        self.serviceModelError.connect(self.toolbar.showModelError)
        self.toolbar.initialize()
        if recoveredDocument is not None:
            self.toolbar.restoreSelection(recoveredDocument['selection'])


    def documentData(self) -> DocumentData:
        """Build persisted data from current exchanges and selections.

        Returns:
            Current versioned WALLO document.
        """
        exchanges = self.conversation.exchangeData()
        currentSelection = self.configManager.getSelection()
        selection: SelectionData = {'profile': currentSelection['profile'], 'service': currentSelection['service'],
                                    'model': currentSelection['model']}
        return self.walloFiles.documentData(exchanges, selection)


    def saveRecovery(self) -> None:
        """Save the current versioned document as crash recovery."""
        self.walloFiles.saveRecovery(self.documentData())


    def loadDocument(self, document: DocumentData) -> None:
        """Apply a validated WALLO document to the main window.

        Args:
            document: Loaded versioned document to display.
        """
        self.conversation.replaceExchanges(document['exchanges'])
        self.toolbar.restoreSelection(document['selection'])
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
        content = self.conversation.content()
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
            self.walloFiles.removeRecovery()


    def _onThreadFinished(self, thread: QThread, worker: Worker) -> None:
        """Drop finished thread/worker references to allow cleanup."""
        if thread in self.activeThreads:
            self.activeThreads.remove(thread)
        if worker in self.activeWorkers:
            self.activeWorkers.remove(worker)


    def activateService(self) -> None:
        """Replace the active service and reset its chat state."""
        if self.activeService is not None:
            self.activeService.stop()
        # Switching service starts a fresh conversation rather than sharing turns across backends.
        self.llmProcessor.resetChat()
        self.activeService = createService(self.configManager)
        self.activeService.getModels(self.serviceModels.emit, self.serviceModelError.emit)


    def onWorkerFinished(self, content: str, senderID: str, workType: str) -> None:
        """Handle the completion of the LLM worker.

        Args:
            content (str): The content generated by the LLM worker.
            senderID (str): The sender ID of the exchange
            workType (str): The type of work performed (e.g., 'chatAPI', 'pdfExtraction')
        """
        processContent = self.llmProcessor.processLLMResponse(content)
        self.conversation.setReply(processContent, senderID, workType)


    def onWorkerError(self, errorMsg: str, senderID: str, workType: str = '') -> None:
        """Handle errors from the LLM worker.

        Args:
            errorMsg (str): The error message from the worker.
            senderID (str): The sender ID of the exchange
            workType (str): The type of work performed (e.g., 'chatAPI', 'pdfExtraction')
        """
        info = f'{errorMsg} by senderID {senderID}'
        QMessageBox.critical(self, 'Worker Error', f'{info} ({workType})' if workType else info)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = Wallo()
    win.resize(1024, 800)
    win.show()
    sys.exit(app.exec())
