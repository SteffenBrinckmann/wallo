""" Custom QTextEdit with word wrap mode set to wrap at word boundary or anywhere. """
from PySide6.QtCore import Qt, Signal  # pylint: disable=no-name-in-module
from PySide6.QtGui import QTextOption, QKeyEvent  # pylint: disable=no-name-in-module
from PySide6.QtWidgets import QApplication, QTextEdit, QVBoxLayout # pylint: disable=no-name-in-module


class TextEdit(QTextEdit):
    """ Custom QTextEdit with word wrap mode set to wrap at word boundary or anywhere. """
    sendMessage = Signal(str)
    def __init__(self) -> None:
        """ Initialize the TextEdit with word wrap mode set to wrap at word boundary or anywhere """
        super().__init__()
        self.setWordWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        self.ideazingMode = False
        self.conversationBlocks:list = []


    def copy(self) -> None:
        """ Copy the selected text to the clipboard """
        cursor = self.textCursor()
        if cursor.hasSelection():
            text = cursor.selectedText()
            print(text)
            QApplication.clipboard().setText(text)
        else:
            super().copy()


    def keyPressEvent(self, event:QKeyEvent) -> None:
        """ Handle key press events for ideazing mode message sending.
        Args:
            event (QKeyEvent): The key press event.
        """
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier and event.key()==Qt.Key.Key_Escape:
            with open('temp_debug.html', 'w', encoding='utf-8') as f:
                f.write(self.toHtml())
        elif self.ideazingMode and event.key() == Qt.Key.Key_Return and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            text = self.toPlainText().strip()
            if text:
                self.sendMessage.emit(text)
            event.accept()
        else:
            super().keyPressEvent(event)


    def setIdeazingMode(self, enabled:bool) -> None:
        """ Enable or disable ideazing mode.
        Args:
            enabled (bool): True to enable ideazing mode, False to disable.
        """
        self.ideazingMode = enabled
