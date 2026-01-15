"""Tab for managing services."""
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
        self.modelLabel = QLabel()
        self.parameterPreview = QTextEdit()
        self.parameterPreview.setReadOnly(True)
        self.parameterPreview.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.parameterPreview.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.parameterPreviewHighlighter = JsonSyntaxHighlighter(self.parameterPreview.document())
        self.typeLabel = QLabel()
        previewLayout.addRow('Name:',    self.nameLabel)
        previewLayout.addRow('URL:',     self.urlLabel)
        previewLayout.addRow('API Key:', self.apiLabel)
        previewLayout.addRow('Model:',   self.modelLabel)
        previewLayout.addRow('Parameter:',   self.parameterPreview)
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
            self.modelLabel.setText(service['model'])
            self.parameterPreview.setPlainText(self._formatJsonPreview(service.get('parameter', '{}')))
            self.typeLabel.setText(service['type'])
        else:
            self.nameLabel.clear()
            self.urlLabel.clear()
            self.apiLabel.clear()
            self.modelLabel.clear()
            self.parameterPreview.clear()
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

    @staticmethod
    def _formatJsonPreview(value: str) -> str:
        if not value:
            return ''
        try:
            parsed = json.loads(value)
            return json.dumps(parsed, indent=2)
        except json.JSONDecodeError:
            return value


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
        self.modelEdit = QLineEdit()
        formLayout.addRow('Model:', self.modelEdit)
        self.parameterEdit = QTextEdit()
        self.parameterHighlighter = JsonSyntaxHighlighter(self.parameterEdit.document())
        formLayout.addRow('Parameter:', self.parameterEdit)
        self.typeEdit = QComboBox()
        self.typeEdit.addItems(['openAI', 'Gemini'])
        self.typeEdit.setCurrentText(self.service['type'])
        formLayout.addRow('Type:', self.typeEdit)
        layout.addLayout(formLayout)
        # Button box
        buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        layout.addWidget(buttonBox)


    def loadService(self) -> None:
        """Load service data into form fields."""
        self.nameEdit.setText(self.serviceName)
        if self.service:
            self.urlEdit.setText(self.service.get('url', ''))
            self.apiEdit.setText(self.service.get('api', '') or '')
            self.modelEdit.setText(self.service.get('model', ''))
            self.parameterEdit.setText(json.dumps(json.loads(self.service.get('parameter', '{}')), indent=2))
            self.typeEdit.setCurrentText(self.service.get('type', 'openAI'))


    def getService(self) -> tuple[str, dict[str, Any]]:
        """Get the service configuration from form fields."""
        name = self.nameEdit.text().strip()
        service = {
            'url': self.urlEdit.text().strip(),
            'api': self.apiEdit.text().strip() or None,
            'model': self.modelEdit.text().strip(),
            'parameter': json.dumps(json.loads(self.parameterEdit.toPlainText())),
            'type': self.typeEdit.currentText()
        }
        return name, service


    def accept(self) -> None:
        """Validate and accept the dialog."""
        name, service = self.getService()
        if not name:
            QMessageBox.warning(self, 'Validation Error', 'Service name cannot be empty')
            return
        if not service['model']:
            QMessageBox.warning(self, 'Validation Error', 'Model cannot be empty')
            return
        super().accept()
