"""Configuration widget for managing application settings."""
from typing import Dict, Any, Optional
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QListWidget,  # pylint: disable=no-name-in-module
                               QPushButton, QLineEdit, QLabel, QFormLayout, QComboBox, QTextEdit, QMessageBox,
                               QDialog, QDialogButtonBox, QListWidgetItem, QGroupBox)
from PySide6.QtCore import Qt, Signal                                                       # pylint: disable=no-name-in-module
from .configManager import ConfigurationManager


class PromptEditDialog(QDialog):
    """Dialog for editing prompt configuration."""

    def __init__(self, prompt: Optional[Dict[str, Any]] = None, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit Prompt" if prompt else "Add Prompt")
        self.setModal(True)
        self.resize(500, 400)
        self.prompt = prompt or {}
        self.setupUI()
        self.loadPrompt()


    def setupUI(self) -> None:
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)
        formLayout = QFormLayout()
        self.nameEdit = QLineEdit()
        formLayout.addRow("Name:", self.nameEdit)
        self.descriptionEdit = QLineEdit()
        formLayout.addRow("Description:", self.descriptionEdit)
        self.userPromptEdit = QTextEdit()
        self.userPromptEdit.setMaximumHeight(100)
        formLayout.addRow("User Prompt:", self.userPromptEdit)
        self.attachmentCombo = QComboBox()
        self.attachmentCombo.addItems(["selection", "pdf", "inquiry"])
        formLayout.addRow("Attachment Type:", self.attachmentCombo)
        layout.addLayout(formLayout)
        # Button box
        buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        layout.addWidget(buttonBox)


    def loadPrompt(self) -> None:
        """Load prompt data into form fields."""
        if self.prompt:
            self.nameEdit.setText(self.prompt.get('name', ''))
            self.descriptionEdit.setText(self.prompt.get('description', ''))
            self.userPromptEdit.setPlainText(self.prompt.get('user-prompt', ''))
            attachment = self.prompt.get('attachment', 'selection')
            index = self.attachmentCombo.findText(attachment)
            if index >= 0:
                self.attachmentCombo.setCurrentIndex(index)


    def getPrompt(self) -> Dict[str, Any]:
        """Get the prompt configuration from form fields."""
        return {
            'name': self.nameEdit.text().strip(),
            'description': self.descriptionEdit.text().strip(),
            'user-prompt': self.userPromptEdit.toPlainText().strip(),
            'attachment': self.attachmentCombo.currentText()
        }


    def accept(self) -> None:
        """Validate and accept the dialog."""
        prompt = self.getPrompt()
        if not prompt['name']:
            QMessageBox.warning(self, "Validation Error", "Name cannot be empty")
            return
        if not prompt['description']:
            QMessageBox.warning(self, "Validation Error", "Description cannot be empty")
            return
        if not prompt['user-prompt']:
            QMessageBox.warning(self, "Validation Error", "User prompt cannot be empty")
            return
        super().accept()


class ServiceEditDialog(QDialog):
    """Dialog for editing service configuration."""

    def __init__(self, serviceName: str = "", service: Optional[Dict[str, Any]] = None,
                 parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit Service" if service else "Add Service")
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
        formLayout.addRow("Service Name:", self.nameEdit)
        self.urlEdit = QLineEdit()
        formLayout.addRow("URL:", self.urlEdit)
        self.apiEdit = QLineEdit()
        formLayout.addRow("API Key:", self.apiEdit)
        self.modelEdit = QLineEdit()
        formLayout.addRow("Model:", self.modelEdit)
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


    def getService(self) -> tuple[str, Dict[str, Any]]:
        """Get the service configuration from form fields."""
        name = self.nameEdit.text().strip()
        service = {
            'url': self.urlEdit.text().strip(),
            'api': self.apiEdit.text().strip() or None,
            'model': self.modelEdit.text().strip()
        }
        return name, service


    def accept(self) -> None:
        """Validate and accept the dialog."""
        name, service = self.getService()
        if not name:
            QMessageBox.warning(self, "Validation Error", "Service name cannot be empty")
            return
        if not service['model']:
            QMessageBox.warning(self, "Validation Error", "Model cannot be empty")
            return
        super().accept()


class PromptTab(QWidget):
    """Tab for managing prompts."""

    def __init__(self, configManager: ConfigurationManager, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.configManager = configManager
        self.setupUI()
        self.loadPrompts()


    def setupUI(self) -> None:
        """Setup the tab UI."""
        layout = QHBoxLayout(self)
        # Left side - prompt list
        leftLayout = QVBoxLayout()
        leftLayout.addWidget(QLabel("Prompts:"))
        self.promptList = QListWidget()
        self.promptList.currentItemChanged.connect(self.onPromptSelectionChanged)
        leftLayout.addWidget(self.promptList)
        # Buttons for prompt management
        buttonLayout = QHBoxLayout()
        self.addPromptBtn = QPushButton("Add")
        self.addPromptBtn.clicked.connect(self.addPrompt)
        self.editPromptBtn = QPushButton("Edit")
        self.editPromptBtn.clicked.connect(self.editPrompt)
        self.editPromptBtn.setEnabled(False)
        self.deletePromptBtn = QPushButton("Remove")
        self.deletePromptBtn.clicked.connect(self.deletePrompt)
        self.deletePromptBtn.setEnabled(False)
        buttonLayout.addWidget(self.addPromptBtn)
        buttonLayout.addWidget(self.editPromptBtn)
        buttonLayout.addWidget(self.deletePromptBtn)
        buttonLayout.addStretch()
        leftLayout.addLayout(buttonLayout)
        # Right side - prompt preview
        rightLayout = QVBoxLayout()
        rightLayout.addWidget(QLabel("Preview:"))
        self.previewGroup = QGroupBox("Prompt Details")
        previewLayout = QFormLayout(self.previewGroup)
        self.nameLabel = QLabel()
        self.descriptionLabel = QLabel()
        self.attachmentLabel = QLabel()
        self.userPromptLabel = QLabel()
        self.userPromptLabel.setWordWrap(True)
        previewLayout.addRow("Name:", self.nameLabel)
        previewLayout.addRow("Description:", self.descriptionLabel)
        previewLayout.addRow("Attachment:", self.attachmentLabel)
        previewLayout.addRow("User Prompt:", self.userPromptLabel)
        rightLayout.addWidget(self.previewGroup)
        rightLayout.addStretch()
        # Add left and right layouts to main layout
        layout.addLayout(leftLayout, 1)
        layout.addLayout(rightLayout, 1)


    def loadPrompts(self) -> None:
        """Load prompts from configuration."""
        self.promptList.clear()
        prompts = self.configManager.get('prompts')
        for prompt in prompts:
            item = QListWidgetItem(prompt['description'])
            item.setData(Qt.ItemDataRole.UserRole, prompt)
            self.promptList.addItem(item)


    def onPromptSelectionChanged(self, current: Optional[QListWidgetItem],
                                 _: Optional[QListWidgetItem]) -> None:
        """Handle prompt selection change."""
        hasSelection = current is not None
        self.editPromptBtn.setEnabled(hasSelection)
        self.deletePromptBtn.setEnabled(hasSelection)
        if current:
            prompt = current.data(Qt.ItemDataRole.UserRole)
            self.nameLabel.setText(prompt['name'])
            self.descriptionLabel.setText(prompt['description'])
            self.attachmentLabel.setText(prompt['attachment'])
            self.userPromptLabel.setText(prompt['user-prompt'])
        else:
            self.nameLabel.clear()
            self.descriptionLabel.clear()
            self.attachmentLabel.clear()
            self.userPromptLabel.clear()


    def addPrompt(self) -> None:
        """Add a new prompt."""
        dialog = PromptEditDialog(parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            newPrompt = dialog.getPrompt()
            prompts = self.configManager.get('prompts')
            prompts.append(newPrompt)
            self.configManager.updateConfig({'prompts': prompts})
            self.loadPrompts()


    def editPrompt(self) -> None:
        """Edit the selected prompt."""
        current = self.promptList.currentItem()
        if not current:
            return
        prompt = current.data(Qt.ItemDataRole.UserRole)
        dialog = PromptEditDialog(prompt, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            updatedPrompt = dialog.getPrompt()
            prompts = self.configManager.get('prompts')
            for i, p in enumerate(prompts):
                if p['name'] == prompt['name']:
                    prompts[i] = updatedPrompt
                    break
            self.configManager.updateConfig({'prompts': prompts})
            self.loadPrompts()


    def deletePrompt(self) -> None:
        """Delete the selected prompt."""
        current = self.promptList.currentItem()
        if not current:
            return
        prompt = current.data(Qt.ItemDataRole.UserRole)
        result = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete the prompt '{prompt['description']}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if result == QMessageBox.StandardButton.Yes:
            prompts = self.configManager.get('prompts')
            prompts = [p for p in prompts if p['name'] != prompt['name']]
            self.configManager.updateConfig({'prompts': prompts})
            self.loadPrompts()


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
        leftLayout.addWidget(QLabel("Services:"))
        self.serviceList = QListWidget()
        self.serviceList.currentItemChanged.connect(self.onServiceSelectionChanged)
        leftLayout.addWidget(self.serviceList)
        # Buttons for service management
        buttonLayout = QHBoxLayout()
        self.addServiceBtn = QPushButton("Add")
        self.addServiceBtn.clicked.connect(self.addService)
        self.editServiceBtn = QPushButton("Edit")
        self.editServiceBtn.clicked.connect(self.editService)
        self.editServiceBtn.setEnabled(False)
        self.deleteServiceBtn = QPushButton("Remove")
        self.deleteServiceBtn.clicked.connect(self.deleteService)
        self.deleteServiceBtn.setEnabled(False)
        buttonLayout.addWidget(self.addServiceBtn)
        buttonLayout.addWidget(self.editServiceBtn)
        buttonLayout.addWidget(self.deleteServiceBtn)
        buttonLayout.addStretch()
        leftLayout.addLayout(buttonLayout)
        # Right side - service preview
        rightLayout = QVBoxLayout()
        rightLayout.addWidget(QLabel("Preview:"))
        self.previewGroup = QGroupBox("Service Details")
        previewLayout = QFormLayout(self.previewGroup)
        self.nameLabel = QLabel()
        self.urlLabel = QLabel()
        self.apiLabel = QLabel()
        self.modelLabel = QLabel()
        previewLayout.addRow("Name:", self.nameLabel)
        previewLayout.addRow("URL:", self.urlLabel)
        previewLayout.addRow("API Key:", self.apiLabel)
        previewLayout.addRow("Model:", self.modelLabel)
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
            self.modelLabel.setText(service.get('model', ''))
        else:
            self.nameLabel.clear()
            self.urlLabel.clear()
            self.apiLabel.clear()
            self.modelLabel.clear()


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
            "Confirm Delete",
            f"Are you sure you want to delete the service '{serviceName}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if result == QMessageBox.StandardButton.Yes:
            services = self.configManager.get('services')
            del services[serviceName]
            self.configManager.updateConfig({'services': services})
            self.loadServices()


class StringTab(QWidget):
    """Tab for managing string configurations."""

    def __init__(self, configManager: ConfigurationManager, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.configManager = configManager
        self.setupUI()
        self.loadStrings()


    def setupUI(self) -> None:
        """Setup the tab UI."""
        layout = QVBoxLayout(self)
        formLayout = QFormLayout()
        self.headerEdit = QLineEdit()
        formLayout.addRow("Header:", self.headerEdit)
        self.footerEdit = QLineEdit()
        formLayout.addRow("Footer:", self.footerEdit)
        self.promptFooterEdit = QTextEdit()
        self.promptFooterEdit.setMaximumHeight(100)
        formLayout.addRow("Prompt Footer:", self.promptFooterEdit)
        layout.addLayout(formLayout)
        buttonLayout = QHBoxLayout()
        self.saveBtn = QPushButton("Save Changes")
        self.saveBtn.clicked.connect(self.saveStrings)
        buttonLayout.addWidget(self.saveBtn)
        buttonLayout.addStretch()
        layout.addLayout(buttonLayout)
        layout.addStretch()


    def loadStrings(self) -> None:
        """Load string configurations."""
        self.headerEdit.setText(self.configManager.get('header'))
        self.footerEdit.setText(self.configManager.get('footer'))
        self.promptFooterEdit.setPlainText(self.configManager.get('promptFooter'))


    def saveStrings(self) -> None:
        """Save string configurations."""
        updates = {
            'header': self.headerEdit.text(),
            'footer': self.footerEdit.text(),
            'promptFooter': self.promptFooterEdit.toPlainText()
        }
        self.configManager.updateConfig(updates)


class ConfigurationWidget(QWidget):
    """Main configuration widget with tabs."""
    configChanged = Signal()

    def __init__(self, configManager: ConfigurationManager, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.configManager = configManager
        self.setupUI()
        self.setWindowTitle("Configuration")
        self.resize(800, 600)


    def setupUI(self) -> None:
        """Setup the main widget UI."""
        layout = QVBoxLayout(self)
        self.tabWidget = QTabWidget()
        self.promptTab = PromptTab(self.configManager)
        self.serviceTab = ServiceTab(self.configManager)
        self.stringTab = StringTab(self.configManager)
        self.tabWidget.addTab(self.promptTab, "Prompts")
        self.tabWidget.addTab(self.serviceTab, "Services")
        self.tabWidget.addTab(self.stringTab, "Strings")
        layout.addWidget(self.tabWidget)

        # Close button
        buttonLayout = QHBoxLayout()
        buttonLayout.addStretch()
        self.closeBtn = QPushButton("Close")
        self.closeBtn.clicked.connect(self.close)
        buttonLayout.addWidget(self.closeBtn)
        layout.addLayout(buttonLayout)


    def closeEvent(self, event: Any) -> None:
        """Handle close event."""
        self.configChanged.emit()
        super().closeEvent(event)
