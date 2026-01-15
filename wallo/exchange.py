"""
Exchange widget which includes
  - text box for entry
  - text box for result show
  - buttons on the right side
"""

from typing import TYPE_CHECKING
import uuid
from pathlib import Path
from PySide6.QtGui import QAction, QKeySequence, QPixmap, QPainter, QPen, QColor, QTransform # pylint: disable=no-name-in-module
from PySide6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QGridLayout, QPushButton, QComboBox, QMessageBox,  # pylint: disable=no-name-in-module
                               QFileDialog, QInputDialog, QLabel)
from PySide6.QtCore import Qt, QEvent, QTimer  # pylint: disable=no-name-in-module
import qtawesome as qta
from .editor import TextEdit
from .misc import ACCENT_COLOR, PushToTalkRecorder
if TYPE_CHECKING:
    from .main import Wallo


class Exchange(QWidget):
    """A tiny prototype exchange widget that echoes messages.

    - `QTextEdit` shows the conversation history (read-only).
    - `QLineEdit` accepts user input. Press Enter or click Send to submit.
    - Replies are simulated with a short delay (echo/backwards text).
    """

    def __init__(self, parent: 'Wallo', text: str = ''):
        """Initialization
        Args:
            parent (QWidget): The parent widget.
        """
        super().__init__(None)
        self.uuid       = uuid.uuid4().hex
        self.btnState   = 'hidden'
        self.mainWidget = parent
        #function states
        self.state      = 0
        self.filePath   = ''
        self.ragUsage   = False
        self.recording  = False
        self.pushToTalkRecorder = PushToTalkRecorder()


        # Build GUI
        self.main  = QHBoxLayout(self)
        self.setObjectName('exchangeWidget')
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet('QWidget#exchangeWidget { border: 1px solid gray; border-radius: 6px; }')
        # Text-Editors
        textLayout = QVBoxLayout()
        self.text1 = TextEdit(self.mainWidget.configManager)
        self.defaultStyle = self.text1.styleSheet()
        self.text1.focused.connect(self.focusThisExchange)
        if text:
            self.text1.setMarkdown(text)
        textLayout.addWidget(self.text1)
        self.text2 = TextEdit(self.mainWidget.configManager)
        self.text2.hide()
        self.text2.focused.connect(self.focusThisExchange)
        textLayout.addWidget(self.text2)
        self.main.addLayout(textLayout)

        # Shortcuts
        self.switchToReplyAction = QAction(self)
        self.switchToReplyAction.setShortcut(QKeySequence('Ctrl+Down'))
        self.switchToReplyAction.setEnabled(False)
        self.switchToReplyAction.triggered.connect(lambda: self.switchEditor('down'))
        self.addAction(self.switchToReplyAction)
        self.switchToHistoryAction = QAction(self)
        self.switchToHistoryAction.setShortcut(QKeySequence('Ctrl+Up'))
        self.switchToHistoryAction.setEnabled(False)
        self.switchToHistoryAction.triggered.connect(lambda: self.switchEditor('up'))
        self.addAction(self.switchToHistoryAction)
        self.btnWidget = QWidget()
        btnLayout  = QGridLayout(self.btnWidget)
        btnLayout.setVerticalSpacing(0)
        btnLayout.setHorizontalSpacing(0)
        self.main.addWidget(self.btnWidget)
        # Buttons
        btns = [
            # x  y  function
            (1, 1, self.hide1),
            (2, 1, self.audio1),
            (3, 1, self.move2to1),
            (1, 2, self.chatExchange),
            (2, 2, self.toggleRag),
            (3, 2, self.attachFile),
            (1, 3, self.splitParagraphs),
            (2, 3, self.addExchangeNext),
            (3, 3, self.clearBoth),

        ]
        shortcuts = {'11':'7','21':'8','31':'9','12':'4','22':'5','32':'6','13':'1','23':'2','33':'3'}
        for x, y, funct in btns:
            name, icon, tooltip = funct(None, True)
            shortcut = 'Alt+' + shortcuts[f'{x}{y}']
            button = QPushButton()
            button.setToolTip(f'{tooltip} ({shortcut})')
            button.setShortcut(QKeySequence(shortcut))
            button.setIcon(qta.icon(icon))
            button.clicked.connect(funct)
            setattr(self, name, button)
            btnLayout.addWidget(button, y, x)
        self.llmCB = QComboBox()
        self.llmCB.setMaximumWidth(120)
        self._populateLlmComboBox()
        self.llmCB.activated.connect(self.useLLM)
        btnLayout.addWidget(self.llmCB, 9, 1, 1, 3)
        # Reserve the button-column space when collapsed: compute width and hide buttons
        self.btnBoxWidth = self.btnWidget.sizeHint().width()
        self.btnControls = self.btnWidget.findChildren(QPushButton) + self.btnWidget.findChildren(QComboBox)
        for control in self.btnControls:
            control.hide()
        # Keep the widget visible but fixed-width so TextEdits don't expand
        self.btnWidget.setFixedWidth(self.btnBoxWidth)

        # Busy overlay (spinner + text)
        self.busyOverlay = QWidget(self)
        self.busyOverlay.hide()
        overlayLayout = QVBoxLayout(self.busyOverlay)
        overlayLayout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.spinnerLabel = QLabel()
        self.spinnerLabel.setFixedSize(48, 48)
        self.spinnerLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.spinnerLabel.setStyleSheet('background-color: rgb(30, 30, 30); border-radius: 6px;')
        overlayLayout.addWidget(self.spinnerLabel, alignment=Qt.AlignmentFlag.AlignCenter)

        self._spinnerBase = self._createSpinnerPixmap(48)
        self.spinnerLabel.setPixmap(self._spinnerBase)

        self.busyText = QLabel('Waiting for LLM…')
        self.busyText.setStyleSheet(f'color: {ACCENT_COLOR}; font-size: 14pt; background-color: rgb(30, 30, 30);'\
                                    ' padding: 6px 12px; border-radius: 6px;')
        overlayLayout.addWidget(self.busyText, alignment=Qt.AlignmentFlag.AlignCenter)
        self._spinAngle = 0
        self._spinnerTimer = QTimer(self)
        self._spinnerTimer.timeout.connect(self._rotateSpinner)


    ### BUTTON FUNCTIONS
    def hide1(self, _: QEvent | None, state: bool = False) -> tuple[str, str, str]:
        """Self-contained function: toggle visibility of first text-box
        Args:
            state (bool): return state
        """
        name       = 'hide1Btn'
        iconOn     = 'fa5s.eye-slash'
        iconOff    = 'fa5s.eye'
        tooltipOn  = 'Hide history'
        tooltipOff = 'Show history'
        if state:
            return name, iconOn, tooltipOn
        if self.text1.isHidden():
            self.text1.show()
            self._setButtonAppearance(name, iconOn, tooltip=tooltipOn)
        else:
            self.text1.hide()
            self._setButtonAppearance(name, iconOff, tooltip=tooltipOff)
        return ('', '', '')


    def clear1(self, _: QEvent | None, state: bool = False) -> tuple[str, str, str]:
        """Self-contained function: clear first text-box
        Args:
            state (bool): return state
        """
        name       = 'clear1Btn'
        icon       = 'mdi.delete'
        tooltip    = 'Delete history'
        if state:
            return name, icon, tooltip
        self.text1.setMarkdown('')
        return ('', '', '')


    def clearBoth(self, _: QEvent | None, state: bool = False) -> tuple[str, str, str]:
        """Self-contained function: clear both text-boxes
        Args:
            state (bool): return state
        """
        name       = 'clearBothBtn'
        icon       = 'mdi.delete-alert'
        tooltip    = 'Delete both'
        if state:
            return name, icon, tooltip
        self.text1.setMarkdown('')
        self.text2.setMarkdown('')
        self.text2.hide()
        return ('', '', '')


    def audio1(self, _: QEvent | None, state: bool = False) -> tuple[str, str, str]:
        """Self-contained function: append audio input via STT to first text-box
        Args:
            state (bool): return state
        """
        name       = 'audio1Btn'
        icon       = 'fa5s.microphone'
        tooltip    = 'Add speech to history'
        if state:
            return name, icon, tooltip
        if self.recording:
            self._setButtonAppearance(name, icon)
            self.recording = False
            path = self.pushToTalkRecorder.stop()
            self.setBusy(True, 'Transcribing…')
            # assemble prompt
            self.mainWidget.runWorker('transcribeAudio', {'runnable':self.mainWidget.llmProcessor.sttParser,
                                                          'senderID':self.uuid, 'path':path})
        else:
            self._setButtonAppearance(name, icon, color=ACCENT_COLOR)
            self.recording = True
            self.pushToTalkRecorder.start()
        return ('', '', '')


    def move2to1(self, _: QEvent | None, state: bool = False) -> tuple[str, str, str]:
        """Self-contained function: move content of 2nd text-box to 1st
        Args:
            state (bool): return state
        """
        name       = 'move2to1Btn'
        icon       = 'fa5s.angle-double-up'
        tooltip    = 'Move answer to history'
        if state:
            return name, icon, tooltip
        self.text1.setMarkdown(self.text2.toMarkdown())
        self.text2.setMarkdown('')
        self.text2.hide()
        self.text1.setStyleSheet(self.defaultStyle)
        return ('', '', '')


    def showStatus(self, _: QEvent | None, state: bool = False) -> tuple[str, str, str]:
        """Self-contained function: Allow to toggle the color of the button: green, red, neutral
        Args:
            state (bool): return state
        """
        name    = 'showStatusBtn'  # different than function name
        icon    = 'fa5s.circle'
        tooltip = 'Toggle state'
        if state:
            return name, icon, tooltip
        if self.state == 0:
            self._setButtonAppearance(name, icon, color='green')
            self.state = 1
        elif self.state == 1:
            self._setButtonAppearance(name, icon, color='red')
            self.state = 2
        elif self.state == 2:
            self._setButtonAppearance(name, icon)
            self.state = 0
        return ('', '', '')



    def toggleRag(self, _: QEvent | None, state: bool = False) -> tuple[str, str, str]:
        """Self-contained function: Allow to toggle RAG usage
        Args:
            state (bool): return state
        """
        name    = 'toggleRagBtn'  # different than function name
        icon    = 'fa5s.database'
        tooltip = 'Toggle database / RAG usage'
        if state:
            return name, icon, tooltip
        if self.ragUsage:
            self._setButtonAppearance(name, icon)
            self.ragUsage = False
        else:
            self._setButtonAppearance(name, icon, color=ACCENT_COLOR)
            self.ragUsage = True
        return ('', '', '')


    def addExchangeNext(self, _: QEvent | None, state: bool = False) -> tuple[str, str, str]:
        """Self-contained function: add an empty exchange after this to the list
        Args:
            state (bool): return state
        """
        name    = 'addExchangeNextBtn'  # different than function name
        icon    = 'fa5s.plus'
        tooltip = 'Add an empty exchange after this'
        if state:
            return name, icon, tooltip
        self.mainWidget.addExchanges(self.uuid, [''])
        return ('', '', '')


    def splitParagraphs(self, _: QEvent | None, state: bool = False) -> tuple[str, str, str]:
        """Self-contained function: split paragraphs into separate exchanges
        Args:
            state (bool): return state
        """
        name    = 'splitParagraphsBtn'  # different than function name
        icon    = 'fa6s.arrows-down-to-line'
        tooltip = 'Split paragraphs of history into separate exchanges'
        if state:
            return name, icon, tooltip
        texts = [i.strip() for i in self.text1.toMarkdown().split('\n\n') if i.strip()]
        self.text1.setMarkdown(texts[0])
        self.mainWidget.addExchanges(self.uuid, texts[1:])
        return ('', '', '')


    def attachFile(self, _event: QEvent | None, state: bool = False) -> tuple[str, str, str]:
        """Self-contained function: attach a file to exchange for summary....
        Args:
            _event (QEvent | None): event
            state (bool): return state
        """
        name    = 'attachFileBtn'  # different than function name
        icon    = 'fa5s.file-medical'
        tooltip = 'Attach a file to supply context'
        if state:
            return name, icon, tooltip
        filePath, _selectedFilter = QFileDialog.getOpenFileName(self, 'Select a pdf-file to add as context',
                                                                str(Path.home()), 'pdf-files (*.pdf)')
        if filePath:
            self.filePath = filePath
            self._setButtonAppearance(name, icon, color=ACCENT_COLOR)
        return ('', '', '')


    def chatExchange(self, _: QEvent | None, state: bool = False) -> tuple[str, str, str]:
        """Self-contained function: chat with LLM in conventional mode
        Args:
            state (bool): return state
        """
        name    = 'chatExchangeBtn'  # different than function name
        icon    = 'mdi.chat'
        tooltip = 'Send to LLM in chat-mode'
        if state:
            return name, icon, tooltip
        text = self.text1.toMarkdown().strip()
        if text:
            self.setBusy(True)
            # LLM
            serviceName  = self.mainWidget.serviceCB.currentText()
            workParams = self.mainWidget.llmProcessor.processPrompt(self.uuid, '', serviceName, text,
                                                                    ragUsage=self.ragUsage)
            self.mainWidget.runWorker('chatAPI', workParams)
        return ('', '', '')

    ### END BUTTON FUNCTIONS

    def useLLM(self, _: int) -> None:
        """Use the selected LLM to process the text in the editor
        Args:
            _ (int): The index of the selected item in the combo box.
        """
        promptName   = self.llmCB.currentData()
        serviceName  = self.mainWidget.serviceCB.currentText()
        promptConfig = self.mainWidget.configManager.getPromptByName(promptName)
        if not promptConfig:
            QMessageBox.warning(self, 'Error', f"Prompt '{promptName}' not found")
            return

        historyPlain = self.text1.toPlainText().strip()
        historyMarkdown = self.text1.toMarkdown()
        if not (self.filePath or historyPlain):
            QMessageBox.information(self, 'Warning', 'No text in upper text-box.')
            return

        userInput = ''
        if promptConfig['inquiry'] and not historyPlain:
            QMessageBox.information(self, 'Warning', 'No text in upper text-box.')
            return
        if promptConfig['inquiry']:
            inquiryText = promptConfig['user-prompt'].split('|')[1]
            userInput, ok = QInputDialog.getText(self, 'Enter input', f"Please enter {inquiryText}")
            if not ok or not userInput:
                return

        self.setBusy(True)

        workParams = self.mainWidget.llmProcessor.processPrompt(self.uuid, promptName, serviceName,
                                                                historyMarkdown, self.filePath,
                                                                userInput, self.ragUsage)
        self.mainWidget.runWorker('chatAPI', workParams)


    def setReply(self, content: str, senderID: str, worktype:str) -> None:
        """ Get reply form LLM and change data of exchange accordingly
        Args:
            content (str): The content generated by the LLM worker.
            senderID (str): The sender ID of the exchange
            worktype (str): The type of work being performed.
        """
        if senderID == self.uuid:
            self.setBusy(False)
            if worktype == 'chatAPI':
                self.text2.show()
                self.text2.setMarkdown(content)
                self.text1.setStyleSheet(f'color: {ACCENT_COLOR}; font-size: 10pt;')
            else:
                self.text1.append(content)


    def setBusy(self, busy: bool, text: str | None = None) -> None:
        """Show/hide busy overlay and spinner."""
        if text is not None:
            self.busyText.setText(text)
        if busy:
            self.busyOverlay.setGeometry(self.rect())
            self.busyOverlay.show()
            self._spinnerTimer.start(50)
        else:
            self._spinnerTimer.stop()
            self.busyOverlay.hide()


    def _setButtonAppearance(self, buttonName: str, icon: str, color: str | None = None,
                             tooltip: str | None = None) -> None:
        """Set a button's icon and (optional) tooltip."""
        button = getattr(self, buttonName)
        button.setIcon(qta.icon(icon) if color is None else qta.icon(icon, color=color))
        if tooltip is not None:
            button.setToolTip(tooltip)


    ### GENERAL FUNCTIONS
    def __repr__(self) -> str:
        """Generate a string representation of the object"""
        historyText = '' if self.text1.isHidden() else self.text1.toMarkdown().strip()
        replyText = '' if self.text2.isHidden() else self.text2.toMarkdown().strip()

        text = f'\n```text\n{historyText}\n```' if historyText else ''
        if replyText:
            text += '\n' + replyText
        return text


    ### FOR DISPLAY OF BUTTON BOX ON RIGHT SIDE
    def focusThisExchange(self) -> None:
        """ User clicks into this exchange..."""
        self.btnState = 'waiting'
        self.mainWidget.changeActive()


    def focusForTyping(self) -> None:
        """Move keyboard focus to the primary editor."""
        if not self.text1.isHidden():
            self.text1.setFocus()
        elif not self.text2.isHidden():
            self.text2.setFocus()


    def showButtons(self) -> None:
        """Activate this exchange:
        - Show the button widgets (keep btnWidget width).
        - Activate actions
        - do not overload with focus tasks
        """
        for control in self.btnControls:
            control.show()
        for action in self.actions():
            action.setEnabled(True)
        self.btnWidget.setFixedWidth(self.btnBoxWidth)
        self.btnState = 'show'
        self._populateLlmComboBox()


    def hideButtons(self) -> None:
        """Deactivate this exchange:
        - Hide only the buttons but keep the btnWidget visible to reserve space.
        - Deactivate actions
        """
        for control in self.btnControls:
            control.hide()
        for action in self.actions():
            action.setEnabled(False)
        self.btnWidget.setFixedWidth(self.btnBoxWidth)
        self.btnState = 'hidden'
        if not self.text2.toMarkdown().strip():
            self.text2.hide()
        self.text1.adjustHeightToContents(1 if self.text2.isHidden() else 2)
        self.text2.adjustHeightToContents(1 if self.text1.isHidden() else 2)



    def _populateLlmComboBox(self) -> None:
        """Populate the LLM combo box with available prompts."""
        self.llmCB.clear()
        # add LLM selections
        prompts = self.mainWidget.configManager.get('prompts')
        for i, prompt in enumerate(prompts):
            if i < 10:  # Limit to Ctrl+1 through Ctrl+9 and Ctrl+0
                shortcutNumber = (i + 1) % 10  # 1-9, then 0 for the 10th item
                shortcut = f"Ctrl+{shortcutNumber}"
                displayText = f"{prompt['name']} ({shortcut})"
                self.llmCB.addItem(displayText, prompt['name'])
                # Create shortcut action
                shortcutAction = QAction(self)
                shortcutAction.setShortcut(QKeySequence(shortcut))
                shortcutAction.setEnabled(False)
                shortcutAction.triggered.connect(lambda _checked=False, index=i: self.useShortcut(index))
                self.addAction(shortcutAction)
            else:
                self.llmCB.addItem(prompt['name'], prompt['name'])


    def useShortcut(self, index: int) -> None:
        """Use LLM via keyboard shortcut.
        Args:
            index (int): The index of the prompt to use.
        """
        if index < self.llmCB.count():
            self.llmCB.setCurrentIndex(index)
            self.useLLM(index)


    def switchEditor(self, direction: str) -> None:
        """Switch focus between editors
        Args:
            direction (str): 'up' or 'down'
        """
        if direction == 'down':
            if self.text1.hasFocus() and not self.text2.isHidden():
                self.text2.setFocus()
        else:
            if self.text2.hasFocus() and not self.text1.isHidden():
                self.text1.setFocus()


    ## SPINNER GRAPHICS
    def _createSpinnerPixmap(self, size: int) -> QPixmap:
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        penBg = QPen(QColor(ACCENT_COLOR), 4)
        penFg = QPen(Qt.GlobalColor.lightGray, 4)
        painter.setPen(penBg)
        painter.drawEllipse(4, 4, size - 8, size - 8)
        painter.setPen(penFg)
        painter.drawArc(4, 4, size - 8, size - 8, 90 * 16, 90 * 16)
        painter.end()
        return pixmap


    def _rotateSpinner(self) -> None:
        self._spinAngle = (self._spinAngle + 30) % 360
        transform = self._spinnerBase.transformed(QTransform().rotate(self._spinAngle),
                                                  Qt.TransformationMode.SmoothTransformation)
        self.spinnerLabel.setPixmap(transform)


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
