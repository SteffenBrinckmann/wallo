"""Main toolbar and its configuration controls."""
from typing import TYPE_CHECKING
import qtawesome as qta
from PySide6.QtGui import QAction, QKeySequence  # pylint: disable=no-name-in-module
from PySide6.QtWidgets import (QComboBox, QFileDialog, QMessageBox, QToolBar, QWidget) # pylint: disable=no-name-in-module
from .configMain import ConfigurationWidget
from .misc import invertIcon
from .walloFiles import SelectionData

if TYPE_CHECKING:
    from .main import Wallo


class Toolbar(QToolBar):
    """Own WALLO toolbar actions, selectors, and configuration UI."""

    def __init__(self, mainWindow: 'Wallo') -> None:
        """Create toolbar controls for a WALLO window.

        Args:
            mainWindow: Application window providing document and worker operations.
        """
        super().__init__('Main', mainWindow)
        self.mainWindow = mainWindow
        self.configManager = mainWindow.configManager
        self.configWidget: ConfigurationWidget | None = None
        self.pendingModel = ''
        self.spellcheck = True
        self.profileCB = QComboBox()
        self.serviceCB = QComboBox()
        self.modelsCB = QComboBox()
        self._build()


    def _build(self) -> None:
        """Create and connect every toolbar control."""
        self.spellIcon = qta.icon('fa5s.spell-check')
        self.spellIconInverted = invertIcon(self.spellIcon)
        self.spellcheckAction = QAction('', self, icon=self.spellIconInverted, checkable=True,
                                        toolTip='Toggle spellchecker')
        self.spellcheckAction.setChecked(self.spellcheck)
        self.spellcheckAction.triggered.connect(self.toggleSpellcheck)
        self.addAction(self.spellcheckAction)
        self.addWidget(self._spacer())
        openAction = QAction('', self, icon=qta.icon('fa5.folder-open'), toolTip='Open WALLO document')
        openAction.triggered.connect(
            lambda: self.mainWindow.walloFiles.openDocument(self.mainWindow, self.mainWindow.loadDocument))
        self.addAction(openAction)
        saveAction = QAction('', self, icon=qta.icon('fa5.save'), toolTip='Save WALLO document')
        saveAction.triggered.connect(
            lambda: self.mainWindow.walloFiles.saveDocument(self.mainWindow, self.mainWindow.documentData()))
        self.addAction(saveAction)
        exportAction = QAction('', self, icon=qta.icon('fa5s.file-export'), toolTip='Export as docx or markdown')
        exportAction.triggered.connect(lambda: self.mainWindow.saveToFile('text'))
        self.addAction(exportAction)
        ttsAction = QAction('', self, icon=qta.icon('fa5.file-audio'), toolTip='Save to mp3 file')
        ttsAction.triggered.connect(lambda: self.mainWindow.saveToFile('tts'))
        self.addAction(ttsAction)
        self.addWidget(self._spacer())
        self.addWidget(self.profileCB)
        self.profileCB.activated.connect(lambda: self.onConfigChanged('profile'))
        self.addSeparator()
        self.addWidget(self.serviceCB)
        self.serviceCB.activated.connect(lambda: self.onConfigChanged('service'))
        self.addWidget(self.modelsCB)
        self.modelsCB.activated.connect(lambda: self.onConfigChanged('model'))
        self.addWidget(self._spacer())
        ragAction = QAction('', self, icon=qta.icon('mdi.database-plus'), toolTip='Add files to knowledge base')
        ragAction.triggered.connect(self.addRagSources)
        self.addAction(ragAction)
        self.addWidget(self._spacer())
        self.agentIcon = qta.icon('fa5s.robot')
        self.agentIconInverted = invertIcon(self.agentIcon)
        self.agentUseAction = QAction('', self, icon=self.agentIcon, toolTip='Allow to use LLM Agents')
        self.agentUseAction.triggered.connect(self.toggleAgentsUse)
        self.addAction(self.agentUseAction)
        self.pastaUseIcon = qta.icon('mdi.pasta')
        self.pastaUseIconInverted = invertIcon(self.pastaUseIcon)
        self.pastaUseAction = QAction('', self, icon=self.pastaUseIcon, toolTip='Link and use PASTA-ELN database')
        self.pastaUseAction.triggered.connect(self.linkPastaELN)
        self.addAction(self.pastaUseAction)
        self.addWidget(self._spacer())
        configAction = QAction('', self, icon=qta.icon('fa5s.cog'), toolTip='Configuration',
                               shortcut=QKeySequence('Ctrl+0'))
        configAction.triggered.connect(self.showConfiguration)
        self.addAction(configAction)


    @staticmethod
    def _spacer(width: int = 20) -> QWidget:
        """Create a fixed-width toolbar spacer.

        Args:
            width: Spacer width in pixels.
        Returns:
            Widget used to separate toolbar groups.
        """
        spacer = QWidget()
        spacer.setFixedWidth(width)
        return spacer


    def initialize(self) -> None:
        """Load configuration choices and activate the first service."""
        self.onConfigChanged('initialize')


    def restoreSelection(self, selection: SelectionData) -> None:
        """Restore available document toolbar selections.

        Args:
            selection: Saved profile, service, and model names.
        """
        unavailable: list[str] = []
        if selection['profile'] in self.configManager.get('profiles'):
            self.profileCB.setCurrentText(selection['profile'])
            self.configManager.set('profile', selection['profile'])
        else:
            unavailable.append(f"profile '{selection['profile']}'")
        if selection['service'] in self.configManager.get('services'):
            self.serviceCB.setCurrentText(selection['service'])
            self.configManager.set('service', selection['service'])
        else:
            unavailable.append(f"service '{selection['service']}'")
        self.pendingModel = selection['model']
        self.mainWindow.activateService()
        if unavailable:
            QMessageBox.warning(self, 'Document Selection', 'Unavailable: ' + ', '.join(unavailable))


    def setModels(self, models: list[str]) -> None:
        """Populate models reported by the active service.

        Args:
            models: Available model names.
        """
        self.modelsCB.clear()
        self.modelsCB.addItems(models)
        self.modelsCB.setEnabled(bool(models))
        if models:
            model = self.pendingModel if self.pendingModel in models else models[0]
            if self.pendingModel and self.pendingModel not in models:
                QMessageBox.warning(self, 'Document Selection', f"Unavailable model '{self.pendingModel}'")
            self.modelsCB.setCurrentText(model)
            self.configManager.set('model', model)
        else:
            self.configManager.set('model', '')
        self.pendingModel = ''
        self.mainWindow.saveRecovery()


    def showModelError(self, errorMsg: str) -> None:
        """Show a service model-discovery error.

        Args:
            errorMsg: Error returned by the active service.
        """
        QMessageBox.critical(self, 'Service Error', errorMsg)


    def toggleSpellcheck(self) -> None:
        """Toggle spell checking for all conversation editors."""
        self.spellcheck = not self.spellcheck
        self.mainWindow.conversation.setSpellcheck(self.spellcheck)
        self.spellcheckAction.setIcon(self.spellIconInverted if self.spellcheck else self.spellIcon)


    def toggleAgentsUse(self) -> None:
        """Toggle API agent-tool use."""
        agents = self.mainWindow.llmProcessor.agents
        agents.useAgents = not agents.useAgents
        self.agentUseAction.setIcon(self.agentIconInverted if agents.useAgents else self.agentIcon)


    def linkPastaELN(self) -> None:
        """Select a PASTA-ELN database for read-only agent context."""
        fileName, _ = QFileDialog.getOpenFileName(self, 'Select a PASTA-ELN database', '',
                                                  'SQLite Files (*.db)')
        if fileName:
            self.mainWindow.llmProcessor.agents.usePastaEln = fileName
            self.pastaUseAction.setIcon(self.pastaUseIconInverted)


    def addRagSources(self) -> None:
        """Select files or a folder to add to the RAG knowledge base."""
        filePaths, _ = QFileDialog.getOpenFileNames(self, 'Select files to add to knowledge base', '', 'All Files (*)')
        if not filePaths:
            if directory := QFileDialog.getExistingDirectory(self, 'Select folder to add to knowledge base'):
                filePaths = [directory]
        if filePaths:
            self.mainWindow.runWorker('ingestRAG', {'runnable': self.mainWindow.llmProcessor.ragIndexer,
                                                     'filePaths': filePaths, 'senderID': 'ingestRAG'})


    def showConfiguration(self) -> None:
        """Show the configuration window."""
        if self.configWidget is None:
            self.configWidget = ConfigurationWidget(self.configManager)
            self.configWidget.configChanged.connect(lambda: self.onConfigChanged('reread'))
        self.configWidget.show()
        self.configWidget.raise_()
        self.configWidget.activateWindow()


    def onConfigChanged(self, dType: str = 'initialize') -> None:
        """Apply a configuration or toolbar selection change.

        Args:
            dType: Changed configuration category or initialization marker.
        """
        if dType == 'reread':
            self.configManager.loadConfig()
            dType = 'initialize'
        if dType == 'initialize':
            self.profileCB.clear()
            self.profileCB.addItems(self.configManager.get('profiles'))
            self.configManager.set('profile', self.configManager.get('profiles')[0])
            self.serviceCB.clear()
            self.serviceCB.addItems(list(self.configManager.get('services').keys()))
            self.configManager.set('service', self.serviceCB.itemText(0))
            self.mainWindow.activateService()
        if dType == 'profile':
            self.configManager.set('profile', self.profileCB.currentText())
            self.mainWindow.saveRecovery()
        if dType == 'service':
            self.configManager.set('service', self.serviceCB.currentText())
            self.mainWindow.activateService()
            self.mainWindow.saveRecovery()
        if dType == 'model':
            self.configManager.set('model', self.modelsCB.currentText())
            self.mainWindow.saveRecovery()
