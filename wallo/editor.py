from PySide6.QtWidgets import QApplication, QTextEdit
from PySide6.QtGui import QClipboard, QTextOption

class TextEdit(QTextEdit):
    def __init__(self):
        """ Initialize the TextEdit with word wrap mode set to wrap at word boundary or anywhere """
        super().__init__()
        self.setWordWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)


    def copy(self):
        """ Copy the selected text to the clipboard """
        cursor = self.textCursor()
        if cursor.hasSelection():
            text = cursor.selectedText()
            print(text)
            QApplication.clipboard().setText(text, QClipboard.Clipboard)
        else:
            super().copy()
