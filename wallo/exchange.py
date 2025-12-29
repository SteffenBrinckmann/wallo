"""
Exchange widget which includes
  - text box for entry
  - text box for result show
  - buttons on the right side
"""
import random
import uuid
from pathlib import Path
from PySide6.QtGui import QAction, QColor, QFont, QKeySequence
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QGridLayout, QTextEdit, QPushButton, QComboBox, QMessageBox, QLineEdit, QFileDialog, QInputDialog
from PySide6.QtCore import Qt, QEvent
import qtawesome as qta
from .example import text
from .editor import TextEdit
from .main import Wallo


class Exchange(QWidget):
    """A tiny prototype exchange widget that echoes messages.

    - `QTextEdit` shows the conversation history (read-only).
    - `QLineEdit` accepts user input. Press Enter or click Send to submit.
    - Replies are simulated with a short delay (echo/backwards text).
    """
    def __init__(self, parent:Wallo):
        """ Initialization
        Args:
            parent (QWidget): The parent widget.
        """
        super().__init__(None)
        self.state = 0
        self.uuid  = uuid.uuid4().hex
        self.btnState = 'hidden'
        self.mainWidget = parent
        self._buildUi()

    def _buildUi(self) -> None:
        """ Build GUI """
        self.main       = QHBoxLayout(self)
        # Text-Editors
        textLayout = QVBoxLayout()
        self.text1 = TextEdit(self.mainWidget.configManager)
        self.text1.focused.connect(self.focusEditors)
        textLayout.addWidget(self.text1)
        self.text2 = TextEdit(self.mainWidget.configManager)
        self.text2.focused.connect(self.focusEditors)
        textLayout.addWidget(self.text2)
        self.main.addLayout(textLayout)
        self.btnWidget = QWidget()
        btnLayout  = QGridLayout(self.btnWidget)
        self.main.addWidget(self.btnWidget)
        # Buttons
        btns = [
            #x  y  function
            (1, 1, self.hide1),
            (2, 1, self.showStatus),
        ]
        for x,y, funct in btns:
            name, icon, tooltip = funct(None, True)
            setattr(self, name, QPushButton())
            getattr(self, name).setToolTip(tooltip)
            getattr(self, name).setIcon(qta.icon(icon))
            getattr(self, name).clicked.connect(funct)
            btnLayout.addWidget(getattr(self, name), y, x)
        self.llmCB     = QComboBox()
        self.llmCB.setMaximumWidth(80)
        self.populateLLM_CB()
        self.llmCB.activated.connect(self.useLLM)
        btnLayout.addWidget(self.llmCB,2,1, 1,2)
        # Reserve the button-column space when collapsed: compute width and hide buttons
        self._btn_width = self.btnWidget.sizeHint().width()
        for btn in self.btnWidget.findChildren(QPushButton):
            btn.hide()
        # Keep the widget visible but fixed-width so TextEdits don't expand
        self.btnWidget.setFixedWidth(self._btn_width)


    def hide1(self, _:QEvent|None, state:bool=False) -> tuple[str, str, str]:
        """ Self-contained function: toggle visibility of first text-box
        Args:
            state (bool): return state
        """
        name      = 'hide1Btn'
        iconOn    = 'fa5s.eye-slash'
        iconOff   = 'fa5s.eye'
        tooltipOn = 'Hide history'
        tooltipOff= 'Show history'
        if state:
            return name, iconOn, tooltipOn
        if self.text1.isHidden():
            self.text1.show()
            self.hide1Btn.setIcon(qta.icon(iconOn)) # type: ignore[attr-defined]
            self.hide1Btn.setToolTip(tooltipOn)     # type: ignore[attr-defined]
        else:
            self.text1.hide()
            self.hide1Btn.setIcon(qta.icon(iconOff)) # type: ignore[attr-defined]
            self.hide1Btn.setToolTip(tooltipOff)     # type: ignore[attr-defined]
        return ('', '', '')


    def showStatus(self, _:QEvent|None, state:bool=False) -> tuple[str, str, str]:
        """ Self-contained function: Allow to toggle the color of the button: green, red, neutral
        Args:
            state (bool): return state
        """
        name    = 'showStatusBtn'  #different than function name
        icon    = 'fa5s.circle'
        tooltip = 'toggle state'
        if state:
            return name, icon, tooltip
        if self.state==0:
            self.showStatusBtn.setIcon(qta.icon(icon, color='green')) # type: ignore[attr-defined]
            self.state=1
        elif self.state==1:
            self.showStatusBtn.setIcon(qta.icon(icon, color='red'))  # type: ignore[attr-defined]
            self.state=2
        elif self.state==2:
            self.showStatusBtn.setIcon(qta.icon(icon))               # type: ignore[attr-defined]
            self.state=0
        return ('', '', '')




    def useLLM(self, _:int) -> None:
        """ Use the selected LLM to process the text in the editor
        Args:
            _ (int): The index of the selected item in the combo box.
        """
        promptName = self.llmCB.currentData()
        serviceName = self.mainWidget.serviceCB.currentText()
        promptConfig = self.mainWidget.configManager.getPromptByName(promptName)
        if not promptConfig:
            QMessageBox.warning(self, 'Error', f"Prompt '{promptName}' not found")
            return
        attachmentType = promptConfig['attachment']
        if attachmentType == 'selection':
            if not self.text1.toPlainText().strip():
                QMessageBox.information(self, 'Warning', 'You have to have text in the upper text-box for the tool to work')
                return
            workParams = self.mainWidget.llmProcessor.processPrompt(self.uuid, promptName, serviceName, self.text1.toMarkdown())
            self.mainWidget.runWorker('chatAPI', workParams)
        elif attachmentType == 'pdf':
            res = QFileDialog.getOpenFileName(self, 'Open pdf file', str(Path.home()), '*.pdf')
            if not res or not res[0]:
                return
            # Validate PDF file
            if not self.mainWidget.documentProcessor.validatePdfFile(res[0]):
                QMessageBox.warning(self, 'Error', 'Invalid PDF file selected')
                return
            workParams = self.mainWidget.llmProcessor.processPrompt(promptName, serviceName, res[0])
            self.mainWidget.runWorker('pdfExtraction', workParams)
        elif attachmentType == 'inquiry':
            if not self.text1.toPlainText().strip():
                QMessageBox.information(self, 'Warning', 'You have to have text in the upper text-box for the tool to work')
                return
            inquiryText = self.mainWidget.llmProcessor.getInquiryText(promptName)
            if not inquiryText:
                QMessageBox.warning(self, 'Error', 'Invalid inquiry prompt configuration')
                return
            userInput, ok = QInputDialog.getText(self, 'Enter input', f"Please enter {inquiryText}")
            if not ok or not userInput:
                return
            workParams = self.mainWidget.llmProcessor.processPrompt(promptName, serviceName, self.text1.toMarkdown(), userInput)
            self.mainWidget.runWorker('chatAPI', workParams)
        else:
            QMessageBox.warning(self, 'Error', f"Unknown attachment type: {attachmentType}")
            return

    def setReply(self, content:str, senderID:str) -> None:
        if senderID==self.uuid:
            self.text2.setMarkdown(content)

    def focusEditors(self) -> None:
        self.btnState = 'waiting'
        self.mainWidget.changeActive()


    def showButtons(self) -> None:
        """Show the button widgets (keep btnWidget width)."""
        for btn in self.btnWidget.findChildren(QPushButton):
            btn.show()
        try:
            self.btnWidget.setFixedWidth(self._btn_width)
        except AttributeError:
            pass
        self.btnState = 'show'


    def hideButtons(self) -> None:
        """Hide only the buttons but keep the btnWidget visible to reserve space."""
        for btn in self.btnWidget.findChildren(QPushButton):
            btn.hide()
        try:
            self.btnWidget.setFixedWidth(self._btn_width)
        except AttributeError:
            pass
        self.btnState = 'hidden'

    def populateLLM_CB(self) -> None:
        """ Populate the LLM combo box with available prompts. """
        self.llmCB.clear()
        # add LLM selections
        prompts = self.mainWidget.configManager.get('prompts')
        for i, prompt in enumerate(prompts):
            if i < 10:  # Limit to Ctrl+1 through Ctrl+9 and Ctrl+0
                shortcutNumber = (i + 1) % 10  # 1-9, then 0 for the 10th item
                shortcut = f"Ctrl+{shortcutNumber}"
                displayText = f"{prompt['description']} ({shortcut})"
                self.llmCB.addItem(displayText, prompt['name'])

                # Create shortcut action
                shortcutAction = QAction(self)
                shortcutAction.setShortcut(QKeySequence(shortcut))
                shortcutAction.triggered.connect(lambda checked, index=i: self.useLLMShortcut(index))
                self.addAction(shortcutAction)
            else:
                self.llmCB.addItem(prompt['description'], prompt['name'])

    def useLLMShortcut(self, index: int) -> None:
        """ Use LLM via keyboard shortcut.
        Args:
            index (int): The index of the prompt to use.
        """
        if index < self.llmCB.count():
            self.llmCB.setCurrentIndex(index)
            self.useLLM(index)



    def __repr__(self) -> str:
        """ Generate a string representation of the object """
        text = '' if  self.text1.isHidden() else self.text1.toMarkdown().strip()
        text += '\n'+self.text2.toMarkdown().strip()
        return text


    def setExampleData(self) -> None:
        """ Populate with example text """
        self.text1.setMarkdown(random.choice(text.split('\n----\n')))



# FOR TESTING: does not pass mypy
# if __name__ == "__main__":
#   import sys
#   from PySide6.QtWidgets import QApplication
#   app = QApplication.instance()
#   app = QApplication(sys.argv)
#   w = Exchange()
#   w.setExampleData()
#   w.resize(520, 360)
#   w.show()
#   app.exec()
