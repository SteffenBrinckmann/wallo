from PySide6.QtWidgets import QApplication, QTextEdit
from PySide6.QtGui import QClipboard, QTextOption

class TextEdit(QTextEdit):
    def __init__(self):
        super().__init__()
        self.setWordWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)


    def copy(self):
        cursor = self.textCursor()
        if cursor.hasSelection():
            text = cursor.selectedText()
            print(text)
            QApplication.clipboard().setText(text, QClipboard.Clipboard)
        else:
            super().copy()
