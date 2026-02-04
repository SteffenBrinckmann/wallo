"""Tab for managing services."""
import copy
import json
from typing import Any, Optional
from PySide6.QtCore import Qt, QRegularExpression  # pylint: disable=no-name-in-module
from PySide6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont, QTextDocument  # pylint: disable=no-name-in-module
from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QFormLayout, QGroupBox, QHBoxLayout, QLabel, # pylint: disable=no-name-in-module
                               QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QPushButton, QTextEdit,
                               QVBoxLayout, QWidget, QComboBox)
from .configManager import ConfigurationManager


class JsonSyntaxHighlighter(QSyntaxHighlighter):
    """Simple JSON highlighting for the parameter editor."""

    def __init__(self, parent: QTextDocument) -> None:
        super().__init__(parent)
        self.keyFormat = self._makeFormat('#9cdcfe')
        self.stringFormat = self._makeFormat('#ce9178')
        self.numberFormat = self._makeFormat('#b5cea8')
        self.keywordFormat = self._makeFormat('#569cd6')
        self.braceFormat = self._makeFormat('#d7ba7d')
        self.colonFormat = self._makeFormat('#d4d4d4')
        self.rules: list[tuple[QRegularExpression, QTextCharFormat]] = [
            (QRegularExpression(r'"([^"\\]|\\.)*"(?=\s*:)'), self.keyFormat),
            (QRegularExpression(r'"([^"\\]|\\.)*"(?!\s*:)'), self.stringFormat),
            (QRegularExpression(r'\b-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?\b'), self.numberFormat),
            (QRegularExpression(r'\b(true|false|null)\b'), self.keywordFormat),
            (QRegularExpression(r'[{}\[\]]'), self.braceFormat),
            (QRegularExpression(r':'), self.colonFormat)
        ]

    def highlightBlock(self, text: str) -> None:
        """Highlight the given text block.
        Args:
            text (str): The text to highlight.
        """
        for pattern, fmt in self.rules:
            matchIterator = pattern.globalMatch(text)
            while matchIterator.hasNext():
                match = matchIterator.next()
                start = match.capturedStart()
                length = match.capturedLength()
                if length > 0:
                    self.setFormat(start, length, fmt)

    @staticmethod
    def _makeFormat(color: str, weight: QFont.Weight = QFont.Weight.Normal) -> QTextCharFormat:
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        fmt.setFontWeight(weight)
        return fmt


class ServiceTab(QWidget):
    """Tab for managing services."""

    def __init__(self, configManager: ConfigurationManager, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.configManager = configManager
        self.setupUI()
        self.loadServices()


    def setupUI(self) -> None:
        """Setup the tab UI."""
        layout = QHBoxLayout(self)
        # Left side - service list
        leftLayout = QVBoxLayout()
        leftLayout.addWidget(QLabel('Services:'))
        self.serviceList = QListWidget()
        self.serviceList.currentItemChanged.connect(self.onServiceSelectionChanged)
        leftLayout.addWidget(self.serviceList)
        # Buttons for service management
        buttonLayout = QHBoxLayout()
        self.addServiceBtn = QPushButton('Add')
        self.addServiceBtn.clicked.connect(self.addService)
        self.editServiceBtn = QPushButton('Edit')
        self.editServiceBtn.clicked.connect(self.editService)
        self.editServiceBtn.setEnabled(False)
        self.deleteServiceBtn = QPushButton('Remove')
        self.deleteServiceBtn.clicked.connect(self.deleteService)
        self.deleteServiceBtn.setEnabled(False)
        buttonLayout.addWidget(self.addServiceBtn)
        buttonLayout.addWidget(self.editServiceBtn)
        buttonLayout.addWidget(self.deleteServiceBtn)
        buttonLayout.addStretch()
        leftLayout.addLayout(buttonLayout)
        # Right side - service preview
        rightLayout = QVBoxLayout()
        rightLayout.addWidget(QLabel('Preview:'))
        self.previewGroup = QGroupBox('Service Details')
        previewLayout = QFormLayout(self.previewGroup)
        self.nameLabel = QLabel()
        self.urlLabel = QLabel()
        self.apiLabel = QLabel()
        self.modelsPreview = QTextEdit()
        self.modelsPreview.setReadOnly(True)
        self.modelsPreview.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.modelsPreview.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.modelsPreviewHighlighter = JsonSyntaxHighlighter(self.modelsPreview.document())
        self.typeLabel = QLabel()
        previewLayout.addRow('Name:',    self.nameLabel)
        previewLayout.addRow('URL:',     self.urlLabel)
        previewLayout.addRow('API Key:', self.apiLabel)
        previewLayout.addRow('Models:',  self.modelsPreview)
        previewLayout.addRow('Type:',    self.typeLabel)

        rightLayout.addWidget(self.previewGroup)
        rightLayout.addStretch()
        # Add left and right layouts to main layout
        layout.addLayout(leftLayout, 1)
        layout.addLayout(rightLayout, 1)


    def loadServices(self) -> None:
        """Load services from configuration."""
        self.serviceList.clear()
        services = self.configManager.get('services')
        for serviceName, service in services.items():
            item = QListWidgetItem(serviceName)
            item.setData(Qt.ItemDataRole.UserRole, (serviceName, service))
            self.serviceList.addItem(item)


    def onServiceSelectionChanged(self, current: Optional[QListWidgetItem],
                                  _: Optional[QListWidgetItem]) -> None:
        """Handle service selection change."""
        hasSelection = current is not None
        self.editServiceBtn.setEnabled(hasSelection)
        self.deleteServiceBtn.setEnabled(hasSelection)
        if current:
            serviceName, service = current.data(Qt.ItemDataRole.UserRole)
            self.nameLabel.setText(serviceName)
            self.urlLabel.setText(service.get('url', ''))
            self.apiLabel.setText('***' if service.get('api') else 'None')
            self.modelsPreview.setPlainText(json.dumps(service.get('models', '{}'), indent=2))
            self.typeLabel.setText(service['type'])
        else:
            self.nameLabel.clear()
            self.urlLabel.clear()
            self.apiLabel.clear()
            self.modelsPreview.clear()
            self.typeLabel.clear()



    def addService(self) -> None:
        """Add a new service."""
        dialog = ServiceEditDialog(parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            serviceName, service = dialog.getService()
            services = self.configManager.get('services')
            services[serviceName] = service
            self.configManager.updateConfig({'services': services})
            self.loadServices()


    def editService(self) -> None:
        """Edit the selected service."""
        current = self.serviceList.currentItem()
        if not current:
            return
        serviceName, service = current.data(Qt.ItemDataRole.UserRole)
        dialog = ServiceEditDialog(serviceName, service, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            newServiceName, updatedService = dialog.getService()
            services = self.configManager.get('services')
            # Remove old service if name changed
            if serviceName != newServiceName:
                del services[serviceName]
            services[newServiceName] = updatedService
            self.configManager.updateConfig({'services': services})
            self.loadServices()


    def deleteService(self) -> None:
        """Delete the selected service."""
        current = self.serviceList.currentItem()
        if not current:
            return
        serviceName, _ = current.data(Qt.ItemDataRole.UserRole)
        result = QMessageBox.question(
            self,
            'Confirm Delete',
            f"Are you sure you want to delete the service '{serviceName}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if result == QMessageBox.StandardButton.Yes:
            services = self.configManager.get('services')
            del services[serviceName]
            self.configManager.updateConfig({'services': services})
            self.loadServices()


class ModelEntryDialog(QDialog):
    """Dialog to add or edit a model entry."""

    def __init__(self, modelName: str = '', parameters: Optional[dict[str, Any]] = None,
                 parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle('Model Entry')
        self.setModal(True)
        self.resize(400, 300)
        self._modelName = modelName
        self._parameters = parameters or {}
        layout = QVBoxLayout(self)
        formLayout = QFormLayout()
        self.nameEdit = QLineEdit(modelName)
        formLayout.addRow('Model Name:', self.nameEdit)
        self.parameterEdit = QTextEdit()
        self.parameterHighlighter = JsonSyntaxHighlighter(self.parameterEdit.document())
        paramText = json.dumps(self._parameters, indent=2) if self._parameters else '{}'
        self.parameterEdit.setText(paramText)
        formLayout.addRow('Parameters:', self.parameterEdit)
        layout.addLayout(formLayout)
        buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        layout.addWidget(buttonBox)

    def accept(self) -> None:
        """Validate name and JSON parameters before accepting."""
        name = self.nameEdit.text().strip()
        if not name:
            QMessageBox.warning(self, 'Validation Error', 'Model name cannot be empty')
            return
        text = self.parameterEdit.toPlainText().strip()
        params: dict[str, Any] = {}
        if text:
            try:
                params = json.loads(text)
            except json.JSONDecodeError as exc:
                QMessageBox.warning(self, 'Validation Error', f'Invalid JSON: {exc.msg}')
                return
        self._modelName = name
        self._parameters = params
        super().accept()

    def getModel(self) -> tuple[str, dict[str, Any]]:
        """Return the entered model name and parameters."""
        return self._modelName, self._parameters


class ServiceEditDialog(QDialog):
    """Dialog for editing service configuration."""

    def __init__(self, serviceName: str = '', service: Optional[dict[str, Any]] = None,
                 parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle('Edit Service' if service else 'Add Service')
        self.setModal(True)
        self.resize(400, 200)
        self.serviceName = serviceName
        self.service = service or {}
        self.models: dict[str, dict[str, float]] = {}
        self.setupUI()
        self.loadService()

    def setupUI(self) -> None:
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)
        formLayout = QFormLayout()
        self.nameEdit = QLineEdit()
        formLayout.addRow('Service Name:', self.nameEdit)
        self.urlEdit = QLineEdit()
        formLayout.addRow('URL:', self.urlEdit)
        self.apiEdit = QLineEdit()
        formLayout.addRow('API Key:', self.apiEdit)
        self.typeEdit = QComboBox()
        self.typeEdit.addItems(['openAI', 'Gemini'])
        self.typeEdit.setCurrentText(self.service.get('type', 'openAI'))
        formLayout.addRow('Type:', self.typeEdit)
        modelsWidget = QWidget()
        modelsLayout = QHBoxLayout(modelsWidget)
        self.modelsList = QListWidget()
        modelsLayout.addWidget(self.modelsList)
        buttonLayout = QVBoxLayout()
        self.addModelBtn = QPushButton('Add')
        self.addModelBtn.clicked.connect(self.addModel)
        buttonLayout.addWidget(self.addModelBtn)
        self.editModelBtn = QPushButton('Edit')
        self.editModelBtn.clicked.connect(self.editModel)
        self.editModelBtn.setEnabled(False)
        buttonLayout.addWidget(self.editModelBtn)
        self.removeModelBtn = QPushButton('Remove')
        self.removeModelBtn.clicked.connect(self.removeModel)
        self.removeModelBtn.setEnabled(False)
        buttonLayout.addWidget(self.removeModelBtn)
        buttonLayout.addStretch()
        modelsLayout.addLayout(buttonLayout)
        formLayout.addRow('Models:', modelsWidget)
        layout.addLayout(formLayout)
        self.modelsList.currentItemChanged.connect(self.onModelSelectionChanged)
        buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        layout.addWidget(buttonBox)

    def loadService(self) -> None:
        """Load service data into form fields."""
        self.nameEdit.setText(self.serviceName)
        self.urlEdit.setText(self.service.get('url', ''))
        self.apiEdit.setText(self.service.get('api', '') or '')
        self.typeEdit.setCurrentText(self.service.get('type', 'openAI'))
        self.models = {name: dict(params) for name, params in self.service.get('models', {}).items()}
        self._refreshModelList()


    def _refreshModelList(self, selectName: Optional[str] = None) -> None:
        """Refresh the model list.
        Args:
            selectName (Optional[str]): The name of the model to select.
        """
        self.modelsList.clear()
        for name in self.models:
            item = QListWidgetItem(name)
            self.modelsList.addItem(item)
            if selectName and name == selectName:
                self.modelsList.setCurrentItem(item)

    def onModelSelectionChanged(self, current: Optional[QListWidgetItem], _: Optional[QListWidgetItem] = None) -> None:
        """Handle model selection change.
        Args:
            current (Optional[QListWidgetItem]): The currently selected model.
        """
        enabled = current is not None
        self.editModelBtn.setEnabled(enabled)
        self.removeModelBtn.setEnabled(enabled)

    def addModel(self) -> None:
        """Add a new model entry."""
        dialog = ModelEntryDialog(parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            name, parameters = dialog.getModel()
            if name in self.models:
                QMessageBox.warning(self, 'Validation Error', 'Model name must be unique')
                return
            self.models[name] = parameters
            self._refreshModelList(selectName=name)

    def editModel(self) -> None:
        """Edit the selected model entry."""
        current = self.modelsList.currentItem()
        if not current:
            return
        name = current.text()
        parameters = self.models.get(name, {})
        dialog = ModelEntryDialog(name, parameters, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            newName, newParameters = dialog.getModel()
            if newName != name and newName in self.models:
                QMessageBox.warning(self, 'Validation Error', 'Model name must be unique')
                return
            del self.models[name]
            self.models[newName] = newParameters
            self._refreshModelList(selectName=newName)

    def removeModel(self) -> None:
        """Remove the selected model."""
        current = self.modelsList.currentItem()
        if not current:
            return
        self.models.pop(current.text(), None)
        self._refreshModelList()

    def getService(self) -> tuple[str, dict[str, Any]]:
        """Get the service configuration from form fields."""
        name = self.nameEdit.text().strip()
        service = {
            'url': self.urlEdit.text().strip(),
            'api': self.apiEdit.text().strip() or None,
            'models': copy.deepcopy(self.models),
            'type': self.typeEdit.currentText()
        }
        return name, service

    def accept(self) -> None:
        """Validate and accept the dialog."""
        name, service = self.getService()
        if not name:
            QMessageBox.warning(self, 'Validation Error', 'Service name cannot be empty')
            return
        if not service['models']:
            QMessageBox.warning(self, 'Validation Error', 'At least one model must be defined')
            return
        super().accept()
