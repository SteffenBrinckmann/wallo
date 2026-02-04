"""Profile configuration tab."""
from typing import Any, Optional

from PySide6.QtCore import Qt, QTimer  # pylint: disable=no-name-in-module
from PySide6.QtGui import QTextOption  # pylint: disable=no-name-in-module
from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QFormLayout, QGroupBox, QHBoxLayout, QLabel,
                               QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QPushButton, QVBoxLayout,
                               QWidget, QTextEdit, QCheckBox)
from qtawesome import icon as qta_icon

from .configManager import ConfigurationManager, ALLOWED_BUTTONS

class ProfileTab(QWidget):
    """Tab for managing profiles and their prompts."""

    SAVE_DELAY_MS = 700

    def __init__(self, configManager: ConfigurationManager, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.configManager = configManager
        self._currentProfile: Optional[dict[str, Any]] = None
        self._currentProfileName = ''
        self._suspendUpdates = False
        self._systemPromptTimer = QTimer(self)
        self._systemPromptTimer.setSingleShot(True)
        self._systemPromptTimer.timeout.connect(self._saveSystemPrompt)
        self.setupUI()
        self.loadProfiles()

    def setupUI(self) -> None:
        """Setup the tab UI."""
        mainLayout = QHBoxLayout(self)
        leftLayout = QVBoxLayout()
        leftLayout.addWidget(QLabel('Profiles:'))
        self.profileList = QListWidget()
        self.profileList.currentItemChanged.connect(self.onProfileSelectionChanged)
        leftLayout.addWidget(self.profileList)
        self.addProfileBtn = QPushButton(' Add')
        self.addProfileBtn.setIcon(qta_icon('fa5s.plus'))
        self.addProfileBtn.clicked.connect(self.addProfile)
        self.deleteProfileBtn = QPushButton(' Remove')
        self.deleteProfileBtn.setIcon(qta_icon('fa5s.trash'))
        self.deleteProfileBtn.clicked.connect(self.deleteProfile)
        self.deleteProfileBtn.setEnabled(False)
        profileBtnLayout = QHBoxLayout()
        profileBtnLayout.addWidget(self.addProfileBtn)
        profileBtnLayout.addWidget(self.deleteProfileBtn)
        profileBtnLayout.addStretch()
        leftLayout.addLayout(profileBtnLayout)
        mainLayout.addLayout(leftLayout, 1)

        rightLayout = QVBoxLayout()
        detailsGroup = QGroupBox('Profile Details')
        detailsLayout = QFormLayout(detailsGroup)
        self.profileNameEdit = QLineEdit()
        self.profileNameEdit.editingFinished.connect(self.onProfileNameEdited)
        detailsLayout.addRow('Name:', self.profileNameEdit)
        self.systemPromptEdit = QTextEdit()
        self.systemPromptEdit.setMinimumHeight(240)
        self.systemPromptEdit.textChanged.connect(self._scheduleSystemPromptSave)
        detailsLayout.addRow('System Prompt:', self.systemPromptEdit)
        self.buttonsEdit = QLineEdit()
        self.buttonsEdit.editingFinished.connect(self.onButtonsEdited)
        detailsLayout.addRow('Buttons:', self.buttonsEdit)
        rightLayout.addWidget(detailsGroup)

        rightLayout.addWidget(QLabel('Prompts:'))
        self.promptList = QListWidget()
        self.promptList.setMaximumHeight(150)
        self.promptList.currentItemChanged.connect(self.onPromptSelectionChanged)
        rightLayout.addWidget(self.promptList)
        promptBtnLayout = QHBoxLayout()
        self.addPromptBtn = QPushButton(' Add')
        self.addPromptBtn.setIcon(qta_icon('fa5s.plus'))
        self.addPromptBtn.clicked.connect(self.addPrompt)
        self.copyPromptBtn = QPushButton(' Copy')
        self.copyPromptBtn.setIcon(qta_icon('fa5s.copy'))
        self.copyPromptBtn.clicked.connect(self.copyPrompt)
        self.copyPromptBtn.setEnabled(False)
        self.editPromptBtn = QPushButton(' Edit')
        self.editPromptBtn.setIcon(qta_icon('fa5s.edit'))
        self.editPromptBtn.clicked.connect(self.editPrompt)
        self.editPromptBtn.setEnabled(False)
        self.deletePromptBtn = QPushButton(' Remove')
        self.deletePromptBtn.setIcon(qta_icon('fa5s.trash'))
        self.deletePromptBtn.clicked.connect(self.deletePrompt)
        self.deletePromptBtn.setEnabled(False)
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
        promptBtnLayout.addWidget(self.addPromptBtn)
        promptBtnLayout.addWidget(self.copyPromptBtn)
        promptBtnLayout.addWidget(self.editPromptBtn)
        promptBtnLayout.addWidget(self.deletePromptBtn)
        promptBtnLayout.addWidget(self.upPromptBtn)
        promptBtnLayout.addWidget(self.downPromptBtn)
        promptBtnLayout.addStretch()
        rightLayout.addLayout(promptBtnLayout)
        self.promptPreview = QTextEdit()
        self.promptPreview.setReadOnly(True)
        self.promptPreview.setWordWrapMode(QTextOption.WrapMode.NoWrap)
        self.promptPreview.setMaximumHeight(180)
        rightLayout.addWidget(self.promptPreview)
        mainLayout.addLayout(rightLayout, 2)

    def loadProfiles(self) -> None:
        """Refresh the profile list."""
        self.profileList.blockSignals(True)
        self.profileList.clear()
        profiles = self.configManager.getProfilesData()
        for profile in profiles:
            item = QListWidgetItem(profile['name'])
            item.setData(Qt.ItemDataRole.UserRole, profile['name'])
            self.profileList.addItem(item)
        self.profileList.blockSignals(False)
        if profiles:
            target = self._currentProfileName or profiles[0]['name']
            self._selectProfileByName(target)
        else:
            self._clearDetails()

    def _selectProfileByName(self, name: str) -> None:
        items = self.profileList.findItems(name, Qt.MatchFlag.MatchExactly)
        if items:
            self.profileList.setCurrentItem(items[0])

    def _clearDetails(self) -> None:
        self._currentProfile = None
        self._currentProfileName = ''
        self._suspendUpdates = True
        self.profileNameEdit.clear()
        self.systemPromptEdit.clear()
        self.buttonsEdit.clear()
        self.promptList.clear()
        self.promptPreview.clear()
        self._suspendUpdates = False
        self.deleteProfileBtn.setEnabled(False)
        self._updatePromptButtonsState()

    def onProfileSelectionChanged(self, current: Optional[QListWidgetItem], _: Optional[QListWidgetItem]) -> None:
        """Handle profile selection changes."""
        if not current:
            self._clearDetails()
            return
        profile_name = current.data(Qt.ItemDataRole.UserRole)
        profile = self.configManager.getProfileByName(profile_name)
        if not profile:
            return
        self._loadProfileDetails(profile)

    def _loadProfileDetails(self, profile: dict[str, Any]) -> None:
        self._currentProfile = profile
        self._currentProfileName = profile['name']
        self.configManager.set('profile', profile['name'])
        self._suspendUpdates = True
        self.profileNameEdit.setText(profile['name'])
        self.systemPromptEdit.setPlainText(profile.get('system-prompt', ''))
        self._systemPromptTimer.stop()
        buttons = profile.get('buttons', [])
        self.buttonsEdit.setText(', '.join(buttons))
        self._suspendUpdates = False
        self.deleteProfileBtn.setEnabled(True)
        self._refreshPromptList()
        if self.promptList.count():
            self.promptList.setCurrentRow(0)

    def addProfile(self) -> None:
        """Add a new profile entry."""
        existing = {item['name'] for item in self.configManager.getProfilesData()}
        name = 'New Profile'
        suffix = 1
        while name in existing:
            name = f'New Profile {suffix}'
            suffix += 1
        profile = {
            'name': name,
            'system-prompt': '',
            'buttons': list(ALLOWED_BUTTONS),
            'prompts': []
        }
        self.configManager.upsertProfile(profile)
        self._currentProfileName = name
        self.loadProfiles()

    def deleteProfile(self) -> None:
        """Remove the selected profile after confirmation."""
        if not self._currentProfile:
            return
        reply = QMessageBox.question(
            self,
            'Delete Profile',
            f"Delete profile '{self._currentProfile['name']}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self.configManager.removeProfile(self._currentProfile['name'])
        self._currentProfileName = ''
        self.loadProfiles()

    def onProfileNameEdited(self) -> None:
        """Store profile name changes inline."""
        if self._suspendUpdates or not self._currentProfile:
            return
        new_name = self.profileNameEdit.text().strip()
        if not new_name:
            QMessageBox.warning(self, 'Validation Error', 'Profile name cannot be empty')
            self.profileNameEdit.setText(self._currentProfile['name'])
            return
        current_name = self._currentProfile['name']
        if new_name == current_name:
            return
        existing_names = {item['name'] for item in self.configManager.getProfilesData() if item['name'] != current_name}
        if new_name in existing_names:
            QMessageBox.warning(self, 'Validation Error', 'Profile name already exists')
            self.profileNameEdit.setText(current_name)
            return
        self._currentProfile['name'] = new_name
        self.configManager.upsertProfile(self._currentProfile, original_name=current_name)
        self._currentProfileName = new_name
        self.loadProfiles()
        self._selectProfileByName(new_name)

    def _scheduleSystemPromptSave(self) -> None:
        if self._suspendUpdates or not self._currentProfile:
            return
        self._systemPromptTimer.start(self.SAVE_DELAY_MS)

    def _saveSystemPrompt(self) -> None:
        if not self._currentProfile:
            return
        value = self.systemPromptEdit.toPlainText().strip()
        if value == self._currentProfile.get('system-prompt', ''):
            return
        self._currentProfile['system-prompt'] = value
        self._persistCurrentProfile()

    def onButtonsEdited(self) -> None:
        """Validate and persist button lists."""
        if self._suspendUpdates or not self._currentProfile:
            return
        raw = self.buttonsEdit.text()
        parsed = [item.strip() for item in raw.split(',') if item.strip()]
        invalid = [item for item in parsed if item not in ALLOWED_BUTTONS]
        if invalid:
            QMessageBox.warning(
                self,
                'Validation Error',
                f"Buttons must be one of: {', '.join(ALLOWED_BUTTONS)}"
            )
            self.buttonsEdit.setText(', '.join(self._currentProfile.get('buttons', [])))
            return
        self._currentProfile['buttons'] = parsed
        self._persistCurrentProfile()

    def _persistCurrentProfile(self) -> None:
        if not self._currentProfile:
            return
        self.configManager.upsertProfile(self._currentProfile)

    def _refreshPromptList(self) -> None:
        self.promptList.blockSignals(True)
        self.promptList.clear()
        if not self._currentProfile:
            self.promptPreview.clear()
            self.promptList.blockSignals(False)
            return
        for prompt in self._currentProfile.get('prompts', []):
            item = QListWidgetItem(prompt['name'])
            item.setData(Qt.ItemDataRole.UserRole, prompt)
            self.promptList.addItem(item)
        self.promptList.blockSignals(False)
        self._updatePromptButtonsState()

    def _updatePromptButtonsState(self) -> None:
        has_selection = self.promptList.currentItem() is not None
        self.copyPromptBtn.setEnabled(has_selection)
        self.editPromptBtn.setEnabled(has_selection)
        self.deletePromptBtn.setEnabled(has_selection)
        idx = self.promptList.currentRow()
        self.upPromptBtn.setEnabled(has_selection and idx > 0)
        self.downPromptBtn.setEnabled(has_selection and idx < self.promptList.count() - 1)

    def onPromptSelectionChanged(self, current: Optional[QListWidgetItem], _: Optional[QListWidgetItem]) -> None:
        self._updatePromptButtonsState()
        if current:
            prompt = current.data(Qt.ItemDataRole.UserRole)
            lines = [f"Inquiry: {'Yes' if prompt.get('inquiry') else 'No'}", '', prompt.get('user-prompt', '')]
            self.promptPreview.setPlainText('\n'.join(lines))
        else:
            self.promptPreview.clear()

    def addPrompt(self) -> None:
        if not self._currentProfile:
            return
        dialog = PromptEditDialog(parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        prompt = dialog.getPrompt()
        self._currentProfile.setdefault('prompts', []).append(prompt)
        self._persistCurrentProfile()
        self._refreshPromptList()
        self.promptList.setCurrentRow(self.promptList.count() - 1)

    def copyPrompt(self) -> None:
        if not self._currentProfile:
            return
        current = self.promptList.currentRow()
        if current < 0:
            return
        prompt = self._currentProfile['prompts'][current]
        new_prompt = {**prompt}
        new_prompt['name'] = f"{prompt['name']} (copy)"
        dialog = PromptEditDialog(new_prompt, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self._currentProfile['prompts'].append(dialog.getPrompt())
        self._persistCurrentProfile()
        self._refreshPromptList()
        self.promptList.setCurrentRow(self.promptList.count() - 1)

    def editPrompt(self) -> None:
        if not self._currentProfile:
            return
        current = self.promptList.currentRow()
        if current < 0:
            return
        prompt = self._currentProfile['prompts'][current]
        dialog = PromptEditDialog(prompt, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self._currentProfile['prompts'][current] = dialog.getPrompt()
        self._persistCurrentProfile()
        self._refreshPromptList()
        self.promptList.setCurrentRow(current)

    def deletePrompt(self) -> None:
        if not self._currentProfile:
            return
        current = self.promptList.currentRow()
        if current < 0:
            return
        prompt = self._currentProfile['prompts'][current]
        reply = QMessageBox.question(
            self,
            'Delete Prompt',
            f"Delete prompt '{prompt['name']}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self._currentProfile['prompts'].pop(current)
        self._persistCurrentProfile()
        self._refreshPromptList()
        next_row = min(current, self.promptList.count() - 1)
        if next_row >= 0:
            self.promptList.setCurrentRow(next_row)

    def movePromptUp(self) -> None:
        if not self._currentProfile:
            return
        idx = self.promptList.currentRow()
        if idx <= 0:
            return
        prompts = self._currentProfile['prompts']
        prompts[idx - 1], prompts[idx] = prompts[idx], prompts[idx - 1]
        self._persistCurrentProfile()
        self._refreshPromptList()
        self.promptList.setCurrentRow(idx - 1)

    def movePromptDown(self) -> None:
        if not self._currentProfile:
            return
        idx = self.promptList.currentRow()
        prompts = self._currentProfile['prompts']
        if idx < 0 or idx >= len(prompts) - 1:
            return
        prompts[idx + 1], prompts[idx] = prompts[idx], prompts[idx + 1]
        self._persistCurrentProfile()
        self._refreshPromptList()
        self.promptList.setCurrentRow(idx + 1)


class PromptEditDialog(QDialog):
    """Dialog for editing prompt configuration."""

    def __init__(self, prompt: Optional[dict[str, Any]] = None, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle('Edit Prompt' if prompt else 'Add Prompt')
        self.setModal(True)
        self.resize(500, 400)
        self.setMaximumHeight(1024)
        self.prompt = prompt or {}
        self.setupUI()
        self.loadPrompt()

    def setupUI(self) -> None:
        layout = QVBoxLayout(self)
        formLayout = QFormLayout()
        self.nameEdit = QLineEdit()
        formLayout.addRow('Name:', self.nameEdit)
        self.userPromptEdit = QTextEdit()
        self.userPromptEdit.setMinimumHeight(150)
        formLayout.addRow('User-Prompt:', self.userPromptEdit)
        self.inquiryCheck = QCheckBox('Treat as inquiry')
        formLayout.addRow('Inquiry:', self.inquiryCheck)
        layout.addLayout(formLayout)
        buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        layout.addWidget(buttonBox)

    def loadPrompt(self) -> None:
        if self.prompt:
            self.nameEdit.setText(self.prompt.get('name', ''))
            self.userPromptEdit.setPlainText(self.prompt.get('user-prompt', ''))
            self.inquiryCheck.setChecked(self.prompt.get('inquiry', False))

    def getPrompt(self) -> dict[str, Any]:
        return {
            'name': self.nameEdit.text().strip(),
            'user-prompt': self.userPromptEdit.toPlainText().strip(),
            'inquiry': self.inquiryCheck.isChecked()
        }

    def accept(self) -> None:
        prompt = self.getPrompt()
        if not prompt['name']:
            QMessageBox.warning(self, 'Validation Error', 'Name cannot be empty')
            return
        if not prompt['user-prompt']:
            QMessageBox.warning(self, 'Validation Error', 'User-prompt cannot be empty')
            return
        super().accept()
