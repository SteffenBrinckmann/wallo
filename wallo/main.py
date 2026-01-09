"""Main window for the Wallo application, providing a text editor with LLM assistance."""

import sys
from pathlib import Path
from typing import Any, Optional
import qtawesome as qta
import pypandoc
from PySide6.QtCore import QThread, Qt  # pylint: disable=no-name-in-module
from PySide6.QtGui import QAction, QKeySequence, QKeyEvent  # pylint: disable=no-name-in-module
from PySide6.QtWidgets import (QApplication, QComboBox, QFileDialog, QMainWindow, QMessageBox,  QToolBar, # pylint: disable=no-name-in-module
                               QVBoxLayout, QWidget, QScrollArea)
from .configManager import ConfigurationManager
from .configMain import ConfigurationWidget
from .exchange import Exchange
from .misc import invertIcon, HELP_TEXT
from .llmProcessor import LLMProcessor
from .worker import Worker

class Wallo(QMainWindow):
    """Main window for the Wallo application, providing a text editor with LLM assistance."""
    def __init__(self) -> None:
        super().__init__()
        # Initialize business logic components
        self.configManager = ConfigurationManager()
        self.beginner = self.configManager.get('startCounts')>0
        if self.beginner:
            self.configManager.updateConfig({'startCounts': self.configManager.get('startCounts')-1})
        self.llmProcessor = LLMProcessor(self.configManager)

        self.configWidget:ConfigurationWidget|None = None
        self.subThread:None|QThread                = QThread()
        self.worker:None|Worker                    = None
        self.spellcheck                            = True
        self.serviceCB                             = QComboBox()
        self.llmSPCB                               = QComboBox()
        self.toolbar: Optional['QToolBar']         = None

        # GUI
        self.setWindowTitle('WALLO - Writing Assistance by Large Language mOdel')
        container = QWidget(self)
        self.mainLayout = QVBoxLayout(container)
        self.mainLayout.setAlignment(Qt.AlignmentFlag.AlignTop)
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
        if self.beginner:
            self.exchanges[0].text1.setMarkdown(HELP_TEXT)

        self.exchanges[0].text1.setMarkdown('What is the capital of Germany?')
        self.exchanges[0].text2.setMarkdown('Berlin')
        self.exchanges[0].text2.show()

        ## Create the toolbar with formatting actions and LLM selection
        self.toolbar = QToolBar('Main')
        self.addToolBar(self.toolbar)
        self.spellIcon = qta.icon('fa5s.spell-check')
        self.spellIconInverted = invertIcon(self.spellIcon)
        self.spellcheckAction = QAction('', self, icon=self.spellIconInverted, checkable=True,
                                        toolTip='Toggle spellchecker')  # Spellcheck
        self.spellcheckAction.triggered.connect(self.toggleSpellcheck)
        self.toolbar.addAction(self.spellcheckAction)
        wideSep1 = QWidget()
        wideSep1.setFixedWidth(20)
        self.toolbar.addWidget(wideSep1)
        # save action
        saveAction = QAction('', self, icon=qta.icon('fa5.save'), toolTip='Save as docx or markdown')  # Save as docx or markdown
        saveAction.triggered.connect(lambda: self.saveToFile('text'))
        self.toolbar.addAction(saveAction)
        ttsAction = QAction('', self, icon=qta.icon('fa5.file-audio'), toolTip='Save to mp3 file')  # Save as docx or markdown
        ttsAction.triggered.connect(lambda: self.saveToFile('tts'))
        self.toolbar.addAction(ttsAction)
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
        wideSep3 = QWidget()
        wideSep3.setFixedWidth(20)
        self.toolbar.addWidget(wideSep3)
        # add RAG ingestion action
        ragAction = QAction('', self, icon=qta.icon('mdi.database-plus'), toolTip='Add files to knowledge base')
        ragAction.triggered.connect(self.addRagSources)
        self.toolbar.addAction(ragAction)
        wideSep4 = QWidget()
        wideSep4.setFixedWidth(20)
        self.toolbar.addWidget(wideSep4)
        # add agents use
        self.agentIcon = qta.icon('fa5s.robot')
        self.agentIconInverted = invertIcon(self.agentIcon)
        self.agentUseAction = QAction('', self, icon=self.agentIcon, toolTip='Allow to use LLM Agents')
        self.agentUseAction.triggered.connect(self.toggleAgentsUse)
        self.toolbar.addAction(self.agentUseAction)
        # add connect to PASTA-ELN
        self.pastaUseIcon = qta.icon('mdi.pasta')
        self.pastaUseIconInverted = invertIcon(self.pastaUseIcon)
        self.pastaUseAction = QAction('', self, icon=self.pastaUseIcon, toolTip='Link and use PASTA-ELN database')
        self.pastaUseAction.triggered.connect(self.linkPastaELN)
        self.toolbar.addAction(self.pastaUseAction)
        # configuration action
        wideSep5 = QWidget()
        wideSep5.setFixedWidth(20)
        self.toolbar.addWidget(wideSep5)
        configAction = QAction('', self, icon=qta.icon('fa5s.cog'), toolTip='Configuration',
                               shortcut=QKeySequence('Ctrl+0'))
        configAction.triggered.connect(self.showConfiguration)
        self.toolbar.addAction(configAction)
        self.onConfigChanged()


    def layoutExchanges(self) -> None:
        """ Put the exchanges into the main layout """
        for i in reversed(range(self.mainLayout.count())):
            widget = self.mainLayout.itemAt(i).widget()
            if widget is not None:
                widget.setParent(None)
        for exchange in self.exchanges:
            self.mainLayout.addWidget(exchange)
        dummy = QWidget()
        self.mainLayout.addWidget(dummy, stretch=2)



    def changeActive(self) -> None:
        """for all exchanges: change the showing of the buttons"""
        for exchange in self.exchanges:
            if exchange.btnState == 'waiting':
                exchange.showButtons()
            else:
                exchange.hideButtons()

    def keyPressEvent(self, event:QKeyEvent) -> None:
        """ Handle key press events
        Args:
            event (QKeyEvent): The key press event.
        """
        if event.key() == Qt.Key.Key_PageDown and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            idxs = [i for i,j in enumerate(self.exchanges) if j.btnState == 'show']
            if idxs and idxs[0]<len(self.exchanges)-1:
                self.exchanges[idxs[0]].hideButtons()
                self.exchanges[idxs[0]+1].showButtons()
                self.exchanges[idxs[0]+1].focusForTyping()
        elif event.key() == Qt.Key.Key_PageUp   and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            idxs = [i for i,j in enumerate(self.exchanges) if j.btnState == 'show']
            if idxs and idxs[0]>0:
                self.exchanges[idxs[0]-1].showButtons()
                self.exchanges[idxs[0]].hideButtons()
                self.exchanges[idxs[0]-1].focusForTyping()
        else:
            super().keyPressEvent(event)


    def addExchanges(self, uuid: str, texts: list[str]) -> None:
        """ Add exchanges
        Args:
          uuid (str): The UUID of the exchange.
          texts (list[str]): texts to be added into new exchanges
        """
        idx = [i.uuid for i in self.exchanges].index(uuid)
        if idx<len(self.exchanges)-1:
            for text in texts:
                self.exchanges.insert(idx+1, Exchange(self, text))
        else:
            for text in texts:
                self.exchanges.append(Exchange(self, text))
        self.layoutExchanges()


    def saveToFile(self, dType: str) -> None:
        """Save the content of the editor as a .docx or .md file.
        Args:
            type (str): The type of file to save (e.g., 'text' or 'tts').
        """
        filterText = 'Word Files (*.docx);;Markdown Files (*.md)' if dType == 'text' else 'Audio Files (*.mp3)'
        filename, _selFilter = QFileDialog.getSaveFileName(self, 'Save to File', str(Path.home()), filterText)
        if not filename:
            return
        content = ''
        for exchange in self.exchanges:
            content += str(exchange)
        if dType == 'text':
            if filename.lower().endswith('.docx'):
                pypandoc.convert_text(content, 'docx', format='md', outputfile=filename,
                                      extra_args=['--standalone'])
            else:
                with open(filename, 'w', encoding='utf-8') as fh:
                    fh.write(content)
        else:
            possOpenAI = self.configManager.getOpenAiServices()
            if not possOpenAI:
                QMessageBox.critical(None, 'Configuration error', 'No OpenAI services configured')
            apiKey=self.configManager.getServiceByName(possOpenAI[0])['api']
            self.runWorker('tts', {'apiKey':apiKey, 'filePaths': filename, 'content': content, 'senderID': 'tts'})


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


    def onWorkerFinished(self, content: str, senderID: str, workType: str) -> None:
        """Handle the completion of the LLM worker.
        Args:
            content (str): The content generated by the LLM worker.
            senderID (str): The sender ID of the exchange
            workType (str): The type of work performed (e.g., 'chatAPI', 'pdfExtraction')
        """
        processContent = self.llmProcessor.processLLMResponse(content)  # remove starting / trailing stuff
        for exchange in self.exchanges:
            exchange.setReply(processContent, senderID, workType)


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


    def toggleAgentsUse(self) -> None:
        """Toggle agent use on or off."""
        self.llmProcessor.agents.useAgents = not self.llmProcessor.agents.useAgents
        self.agentUseAction.setIcon(self.agentIconInverted if self.llmProcessor.agents.useAgents else self.agentIcon)


    def linkPastaELN(self) -> None:
        """Toggle PASTA-ELN use on or off."""
        filename = QFileDialog.getOpenFileName(self, 'Select a PASTA-ELN database', str(Path.home()),
                                               'SQLite Files (*.db)')
        if filename:
            self.llmProcessor.agents.usePastaEln = filename[0]
            self.pastaUseAction.setIcon(self.pastaUseIconInverted)


    def addRagSources(self) -> None:
        """Open a file or folder dialog to add sources to the RAG knowledge base."""
        filePaths, _ = QFileDialog.getOpenFileNames(self, 'Select files to add to knowledge base', '','All Files (*)')
        if not filePaths:
            directory = QFileDialog.getExistingDirectory(self, 'Select folder to add to knowledge base')
            if directory:
                filePaths = [directory]
        if not filePaths:
            return
        self.runWorker('ingestRAG', {'runnable':self.llmProcessor.ragIndexer, 'filePaths': filePaths})


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
