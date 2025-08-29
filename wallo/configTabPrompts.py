"""Tab for managing prompts."""
from enum import Enum
from typing import Any, Optional

from PySide6.QtCore import Qt  # pylint: disable=no-name-in-module
from PySide6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QFormLayout, QGroupBox, QHBoxLayout, # pylint: disable=no-name-in-module
                               QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QPushButton,
                               QTextEdit, QVBoxLayout, QWidget)
from qtawesome import icon as qta_icon

from .configFileManager import ConfigurationManager


class PromptType(Enum):
    """Type of prompt."""
    PROMPT = 1
    SYSTEM_PROMPT = 2


class PromptTab(QWidget):
    """Tab for managing prompts."""

    def __init__(self, configManager: ConfigurationManager, cType:PromptType, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.configManager = configManager
        self.cType = cType
        self.prompts = 'prompts' if self.cType == PromptType.PROMPT else 'system-prompts'
        self.setupUI()
        self.loadPrompts()


    def setupUI(self) -> None:
        """Setup the tab UI."""
        layout = QHBoxLayout(self)
        # Left side - prompt list
        leftLayout = QVBoxLayout()
        leftLayout.addWidget(QLabel('Prompts:'))
        self.promptList = QListWidget()
        self.promptList.currentItemChanged.connect(self.onPromptSelectionChanged)
        leftLayout.addWidget(self.promptList)
        # Buttons for prompt management
        buttonLayout = QHBoxLayout()
        # Use icons for buttons
        self.addPromptBtn = QPushButton(' Add')
        self.addPromptBtn.setIcon(qta_icon('fa5s.plus'))
        self.addPromptBtn.clicked.connect(self.addPrompt)
        self.editPromptBtn = QPushButton(' Edit')
        self.editPromptBtn.setIcon(qta_icon('fa5s.edit'))
        self.editPromptBtn.clicked.connect(self.editPrompt)
        self.editPromptBtn.setEnabled(False)
        self.deletePromptBtn = QPushButton(' Remove')
        self.deletePromptBtn.setIcon(qta_icon('fa5s.trash'))
        self.deletePromptBtn.clicked.connect(self.deletePrompt)
        self.deletePromptBtn.setEnabled(False)
        buttonLayout.addWidget(self.addPromptBtn)
        buttonLayout.addWidget(self.editPromptBtn)
        buttonLayout.addWidget(self.deletePromptBtn)
        # Up/Down buttons for ordering
        self.upPromptBtn = QPushButton()
        self.upPromptBtn.setIcon(qta_icon('fa5s.arrow-up'))
        self.upPromptBtn.setToolTip('Move selected prompt up')
        self.upPromptBtn.clicked.connect(self.movePromptUp)
        self.upPromptBtn.setEnabled(False)
        self.downPromptBtn = QPushButton()
        self.downPromptBtn.setIcon(qta_icon('fa5s.arrow-down'))
        self.downPromptBtn.setToolTip('Move selected prompt down')
        self.downPromptBtn.clicked.connect(self.movePromptDown)
        self.downPromptBtn.setEnabled(False)
        buttonLayout.addWidget(self.upPromptBtn)
        buttonLayout.addWidget(self.downPromptBtn)
        buttonLayout.addStretch()
        leftLayout.addLayout(buttonLayout)
        # Right side - prompt preview
        rightLayout = QVBoxLayout()
        rightLayout.addWidget(QLabel('Preview:'))
        self.previewGroup = QGroupBox('Prompt Details')
        previewLayout = QFormLayout(self.previewGroup)
        self.nameLabel = QLabel()
        previewLayout.addRow('Name:', self.nameLabel)
        self.userPromptLabel = QLabel()
        self.userPromptLabel.setWordWrap(True)
        if self.cType == PromptType.PROMPT:
            self.descriptionLabel = QLabel()
            self.attachmentLabel = QLabel()
            previewLayout.addRow('Description:', self.descriptionLabel)
            previewLayout.addRow('Attachment:', self.attachmentLabel)
            previewLayout.addRow('User-Prompt:', self.userPromptLabel)
        else:
            previewLayout.addRow('System-Prompt:', self.userPromptLabel)
        rightLayout.addWidget(self.previewGroup)
        rightLayout.addStretch()
        # Add left and right layouts to main layout
        layout.addLayout(leftLayout, 1)
        layout.addLayout(rightLayout, 1)


    def loadPrompts(self) -> None:
        """Load prompts from configuration."""
        self.promptList.clear()
        prompts = self.configManager.get(self.prompts)
        if self.cType == PromptType.PROMPT:
            for prompt in prompts:
                item = QListWidgetItem(prompt['description'])
                item.setData(Qt.ItemDataRole.UserRole, prompt)
                self.promptList.addItem(item)
        else:
            for prompt in prompts:
                item = QListWidgetItem(prompt['name'])
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
            if self.cType == PromptType.PROMPT:
                self.descriptionLabel.setText(prompt['description'])
                self.attachmentLabel.setText(prompt['attachment'])
                self.userPromptLabel.setText(prompt['user-prompt'])
            else:
                self.userPromptLabel.setText(prompt['system-prompt'])
            # enable move buttons when selection exists
            self.upPromptBtn.setEnabled(True)
            self.downPromptBtn.setEnabled(True)
        else:
            self.nameLabel.clear()
            if self.cType == PromptType.PROMPT:
                self.descriptionLabel.clear()
                self.attachmentLabel.clear()
            self.userPromptLabel.clear()
            self.upPromptBtn.setEnabled(False)
            self.downPromptBtn.setEnabled(False)


    def addPrompt(self) -> None:
        """Add a new prompt."""
        dialog = PromptEditDialog(cType=self.cType, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            newPrompt = dialog.getPrompt()
            prompts = self.configManager.get(self.prompts)
            prompts.append(newPrompt)
            self.configManager.updateConfig({self.prompts: prompts})
            self.loadPrompts()


    def editPrompt(self) -> None:
        """Edit the selected prompt."""
        current = self.promptList.currentItem()
        if not current:
            return
        prompt = current.data(Qt.ItemDataRole.UserRole)
        dialog = PromptEditDialog(prompt, cType=self.cType, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            updatedPrompt = dialog.getPrompt()
            prompts = self.configManager.get(self.prompts)
            for i, p in enumerate(prompts):
                if p['name'] == prompt['name']:
                    prompts[i] = updatedPrompt
                    break
            self.configManager.updateConfig({self.prompts: prompts})
            self.loadPrompts()


    def deletePrompt(self) -> None:
        """Delete the selected prompt."""
        current = self.promptList.currentItem()
        if not current:
            return
        prompt = current.data(Qt.ItemDataRole.UserRole)
        result = QMessageBox.question(
            self,
            'Confirm Delete',
            f"Are you sure you want to delete the prompt '{prompt['description']}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if result == QMessageBox.StandardButton.Yes:
            prompts = self.configManager.get('prompts')
            prompts = [p for p in prompts if p['name'] != prompt['name']]
            self.configManager.updateConfig({'prompts': prompts})
            self.loadPrompts()

    def movePromptUp(self) -> None:
        """Move the selected prompt up in the list."""
        current = self.promptList.currentItem()
        if not current:
            return
        idx = self.promptList.currentRow()
        if idx <= 0:
            return
        prompts = self.configManager.get(self.prompts)
        prompts[idx-1], prompts[idx] = prompts[idx], prompts[idx-1]
        self.configManager.updateConfig({self.prompts: prompts})
        self.loadPrompts()
        self.promptList.setCurrentRow(idx-1)


    def movePromptDown(self) -> None:
        """Move the selected prompt down in the list."""
        current = self.promptList.currentItem()
        if not current:
            return
        prompts = self.configManager.get(self.prompts)
        idx = self.promptList.currentRow()
        if idx < 0 or idx >= len(prompts)-1:
            return
        prompts[idx+1], prompts[idx] = prompts[idx], prompts[idx+1]
        self.configManager.updateConfig({self.prompts: prompts})
        self.loadPrompts()
        self.promptList.setCurrentRow(idx+1)


class PromptEditDialog(QDialog):
    """Dialog for editing prompt configuration."""

    def __init__(self, prompt: Optional[dict[str, Any]] = None, cType:PromptType=PromptType.PROMPT,
                 parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle('Edit Prompt' if prompt else 'Add Prompt')
        self.setModal(True)
        self.resize(500, 400)
        self.prompt = prompt or {}
        self.cType = cType
        self.setupUI()
        self.loadPrompt()


    def setupUI(self) -> None:
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)
        formLayout = QFormLayout()
        self.nameEdit = QLineEdit()
        formLayout.addRow('Name:', self.nameEdit)
        if self.cType == PromptType.PROMPT:
            self.descriptionEdit = QLineEdit()
            formLayout.addRow('Description:', self.descriptionEdit)
        self.userPromptEdit = QTextEdit()
        if self.cType == PromptType.PROMPT:
            self.userPromptEdit.setMinimumHeight(150)
            self.userPromptEdit.setMaximumHeight(200)
            formLayout.addRow('User-Prompt:', self.userPromptEdit)
            self.attachmentCombo = QComboBox()
            self.attachmentCombo.addItems(['selection', 'pdf', 'inquiry'])
            formLayout.addRow('Attachment Type:', self.attachmentCombo)
        else:
            self.userPromptEdit.setMinimumHeight(500)
            self.userPromptEdit.setMaximumHeight(600)
            formLayout.addRow('System-Prompt:', self.userPromptEdit)
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
            if self.cType == PromptType.PROMPT:
                self.userPromptEdit.setPlainText(self.prompt.get('user-prompt', ''))
                self.descriptionEdit.setText(self.prompt.get('description', ''))
                attachment = self.prompt.get('attachment', 'selection')
                index = self.attachmentCombo.findText(attachment)
                if index >= 0:
                    self.attachmentCombo.setCurrentIndex(index)
            else:
                self.userPromptEdit.setPlainText(self.prompt.get('system-prompt', ''))


    def getPrompt(self) -> dict[str, Any]:
        """Get the prompt configuration from form fields."""
        if self.cType == PromptType.PROMPT:
            return {
                'name': self.nameEdit.text().strip(),
                'description': self.descriptionEdit.text().strip(),
                'user-prompt': self.userPromptEdit.toPlainText().strip(),
                'attachment': self.attachmentCombo.currentText()
            }
        return {
            'name': self.nameEdit.text().strip(),
            'system-prompt': self.userPromptEdit.toPlainText().strip(),
        }



    def accept(self) -> None:
        """Validate and accept the dialog."""
        prompt = self.getPrompt()
        if not prompt['name']:
            QMessageBox.warning(self, 'Validation Error', 'Name cannot be empty')
            return
        if self.cType == PromptType.PROMPT:
            if not prompt['description']:
                QMessageBox.warning(self, 'Validation Error', 'Description cannot be empty')
                return
            if not prompt['user-prompt']:
                QMessageBox.warning(self, 'Validation Error', 'User-prompt cannot be empty')
                return
        else:
            if not prompt['system-prompt']:
                QMessageBox.warning(self, 'Validation Error', 'System-prompt cannot be empty')
                return
        super().accept()
