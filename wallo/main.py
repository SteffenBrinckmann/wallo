"""Main window for the Wallo application, providing a text editor with LLM assistance."""

import sys
from typing import Any, Optional
import qtawesome as qta
from PySide6.QtCore import QThread  # pylint: disable=no-name-in-module
from PySide6.QtGui import QAction, QKeySequence  # pylint: disable=no-name-in-module
from PySide6.QtWidgets import (QApplication, QComboBox, QFileDialog, QMainWindow, QMessageBox,  QToolBar, # pylint: disable=no-name-in-module
                               QVBoxLayout, QWidget, QScrollArea)
from .configFileManager import ConfigurationManager
from .configMain import ConfigurationWidget
from .docxExport import DocxExporter
from .misc import invertIcon
from .llmProcessor import LLMProcessor
from .pdfDocumentProcessor import PdfDocumentProcessor
from .worker import Worker
from .exchange import Exchange

class Wallo(QMainWindow):
    """Main window for the Wallo application, providing a text editor with LLM assistance."""
    def __init__(self) -> None:
        super().__init__()
        # Initialize business logic components
        self.configManager = ConfigurationManager()
        self.llmProcessor = LLMProcessor(self.configManager)
        self.documentProcessor = PdfDocumentProcessor()
        self.configWidget: ConfigurationWidget | None = None
        self.docxExporter = DocxExporter(self)
        self.subThread:None|QThread = QThread()
        self.worker:None|Worker = None
        self.spellcheck = True
        self.serviceCB = QComboBox()
        self.llmSPCB   = QComboBox()
        self.toolbar: Optional['QToolBar'] = None

        # GUI
        self.setWindowTitle('WALLO - Writing Assistance by Large Language mOdel')
        container = QWidget(self)
        self.mainLayout = QVBoxLayout(container)
        self.exchanges = []
        for _ in range(2):
            exchange = Exchange(self)
            self.exchanges.append(exchange)
        scrollArea = QScrollArea(self)
        scrollArea.setWidgetResizable(True)
        scrollArea.setWidget(container)
        self.setCentralWidget(scrollArea)
        self.layoutExchanges()
        self.exchanges[0].showButtons()

        ## Create the toolbar with formatting actions and LLM selection
        self.toolbar = QToolBar('Main')
        self.addToolBar(self.toolbar)
        self.spellIcon = qta.icon('fa5s.spell-check')
        self.spellIconInverted = invertIcon(self.spellIcon)
        self.spellcheckAction = QAction('', self, icon=self.spellIconInverted, checkable=True, toolTip='Toggle spellchecker')  # Spellcheck
        self.spellcheckAction.triggered.connect(self.toggleSpellcheck)
        self.toolbar.addAction(self.spellcheckAction)
        wideSep1 = QWidget()
        wideSep1.setFixedWidth(20)
        self.toolbar.addWidget(wideSep1)
        # save action
        saveAction = QAction('', self, icon=qta.icon('fa5.save'), toolTip='Save as docx or markdown')  # Save as docx or markdown
        saveAction.triggered.connect(self.saveToFile)
        self.toolbar.addAction(saveAction)
        wideSep2 = QWidget()
        wideSep2.setFixedWidth(20)
        self.toolbar.addWidget(wideSep2)
        # add system prompt selection
        self.llmSPCB = QComboBox()
        self.toolbar.addWidget(self.llmSPCB)
        # add service selection
        self.toolbar.addSeparator()
        self.serviceCB = QComboBox()
        self.toolbar.addWidget(self.serviceCB)
        # add RAG ingestion action
        ragAction = QAction('', self, icon=qta.icon('fa5s.database'), toolTip='Add files to knowledge base')
        ragAction.triggered.connect(self.addRagSources)
        self.toolbar.addAction(ragAction)
        # configuration action
        configAction = QAction('', self, icon=qta.icon('fa5s.cog'), toolTip='Configuration',
                               shortcut=QKeySequence('Ctrl+0'))
        configAction.triggered.connect(self.showConfiguration)
        self.toolbar.addAction(configAction)
        self.onConfigChanged()


    def layoutExchanges(self) -> None:
        """ Put the exchanges into the main layout """
        for widget in self.mainLayout.children():
            widget.deleteLater()
        for exchange in self.exchanges:
            self.mainLayout.addWidget(exchange)
        self.mainLayout.addStretch(2)


    def changeActive(self) -> None:
        """for all exchanges: change the showing of the buttons"""
        for exchange in self.exchanges:
            if exchange.btnState == 'waiting':
                exchange.showButtons()
            else:
                exchange.hideButtons()


    def addExchanges(self, uuid: str, texts: list[str]) -> None:
        """ Add exchanges """
        idx = [i.uuid for i in self.exchanges].index(uuid)
        if idx<len(self.exchanges)-1:
            for text in texts:
                self.exchanges.insert(idx+1, Exchange(self, text))
        else:
            for text in texts:
                self.exchanges.append(Exchange(self, text))
        self.layoutExchanges()


    def saveToFile(self) -> None:
        """Save the content of the editor as a .docx or .md file."""
        filename, selectedFilter = QFileDialog.getSaveFileName(self, 'Save to File', '',
                                                               'Word Files (*.docx);;Markdown Files (*.md)')
        if (filename and selectedFilter.startswith('Word') or filename.lower().endswith('.docx')):
            pass
            # self.docxExporter.exportToDocx(self.editor, filename)
        elif filename:
            # mdText = self.editor.toMarkdown()
            mdText = 'Test'
            with open(filename, 'w', encoding='utf-8') as fh:
                fh.write(mdText)


    def runWorker(self, workType: str, work: dict[str, Any]) -> None:
        """Run a worker thread to perform the specified work -> keep GUI responsive.
        Args:
            workType (str): The type of work to be performed (e.g., 'chatAPI', 'pdfExtraction').
            work (dict): The work parameters, such as client, model, prompt, and fileName.
        """
        self.subThread = QThread()
        self.worker = Worker(workType, work)
        self.worker.moveToThread(self.subThread)
        self.subThread.started.connect(self.worker.run)
        self.worker.finished.connect(self.onWorkerFinished)
        self.worker.error.connect(self.onWorkerError)
        self.worker.finished.connect(self.subThread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.subThread.finished.connect(self.subThread.deleteLater)
        self.subThread.start()


    def onWorkerFinished(self, content: str, senderID: str) -> None:
        """Handle the completion of the LLM worker.
        Args:
            content (str): The content generated by the LLM worker.
        """
        processContent = self.llmProcessor.processLLMResponse(content)  # remove starting / trailing stuff
        for exchange in self.exchanges:
            exchange.setReply(processContent, senderID)


    def onWorkerError(self, errorMsg: str, senderID: str) -> None:
        """Handle errors from the LLM worker.
        Args:
            errorMsg (str): The error message from the worker.
            senderID (str): The sender ID of the exchange
        """
        QMessageBox.critical(self, 'Worker Error', f"{errorMsg} by senderID {senderID}")


    def toggleSpellcheck(self) -> None:
        """Toggle spell checking on or off."""
        self.spellcheck = not self.spellcheck
        for exchange in self.exchanges:
            exchange.text1.setSpellCheckEnabled(self.spellcheck)
            exchange.text2.setSpellCheckEnabled(self.spellcheck)
        self.spellcheckAction.setIcon(self.spellIconInverted if self.spellcheck else self.spellIcon)


    def addRagSources(self) -> None:
        """Open a file or folder dialog to add sources to the RAG knowledge base.

        This is UI-only for now; ingestion is handled elsewhere.
        """
        filePaths, _ = QFileDialog.getOpenFileNames(
            self,
            'Select files to add to knowledge base',
            '',
            'All Files (*)'
        )
        if not filePaths:
            directory = QFileDialog.getExistingDirectory(
                self,
                'Select folder to add to knowledge base'
            )
            if directory:
                filePaths = [directory]
        if not filePaths:
            return
        # Placeholder: actual ingestion will be wired in the RAG implementation
        QMessageBox.information(
            self,
            'RAG sources selected',
            f"Selected {len(filePaths)} path(s) for knowledge ingestion."
        )


    def showConfiguration(self) -> None:
        """Show the configuration widget."""
        if self.configWidget is None:
            self.configWidget = ConfigurationWidget(self.configManager)
            self.configWidget.configChanged.connect(self.onConfigChanged)
        self.configWidget.show()
        self.configWidget.raise_()
        self.configWidget.activateWindow()


    def onConfigChanged(self) -> None:
        """Handle configuration changes."""
        self.llmSPCB.clear()
        systemPrompts = self.configManager.get('system-prompts')
        for prompt in systemPrompts:
            self.llmSPCB.addItem(prompt['name'])
        self.llmSPCB.activated.connect(self.changeSystemPrompt)
        self.serviceCB.clear()
        services = self.configManager.get('services')
        if isinstance(services, dict):
            self.serviceCB.addItems(list(services.keys()))


    def changeSystemPrompt(self, _: int) -> None:
        """Change the system prompt used by the LLM.
        Args:
            _ (int): The index of the selected system prompt.
        """
        promptName = self.llmSPCB.currentText()
        try:
            self.llmProcessor.setSystemPrompt(promptName)
        except Exception as e:
            QMessageBox.critical(self, 'Error', f"An unexpected error occurred: {str(e)}")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = Wallo()
    win.resize(1024, 800)
    win.show()
    sys.exit(app.exec())
