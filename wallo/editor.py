""" Custom QTextEdit with word wrap mode set to wrap at word boundary or anywhere. """
from PySide6.QtWidgets import QApplication, QTextEdit # pylint: disable=no-name-in-module
from PySide6.QtGui import QTextOption                 # pylint: disable=no-name-in-module

class TextEdit(QTextEdit):
    """ Custom QTextEdit with word wrap mode set to wrap at word boundary or anywhere. """
    def __init__(self) -> None:
        """ Initialize the TextEdit with word wrap mode set to wrap at word boundary or anywhere """
        super().__init__()
        self.setWordWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)


    def copy(self) -> None:
        """ Copy the selected text to the clipboard """
        cursor = self.textCursor()
        if cursor.hasSelection():
            text = cursor.selectedText()
            print(text)
            QApplication.clipboard().setText(text)
        else:
            super().copy()
