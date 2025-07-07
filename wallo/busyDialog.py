""" Class for displaying a busy dialog with a progress bar."""
from typing import Optional
from PySide6.QtWidgets import QProgressBar, QDialog, QVBoxLayout, QLabel, QWidget  # pylint: disable=no-name-in-module

class BusyDialog(QDialog):
    """ Class for displaying a busy dialog with a progress bar."""
    def __init__(self, message:str="Working...", parent:Optional[QWidget]=None) -> None:
        """Initialize the BusyDialog with a message and parent widget.
        Args:
            message (str): The message to display in the dialog.
            parent (QWidget, optional): The parent widget for the dialog.
        """
        super().__init__(parent)
        self.setWindowTitle("Please wait")
        self.setModal(True)
        layout = QVBoxLayout(self)
        self.label = QLabel(message)
        layout.addWidget(self.label)
        self.progressBar = QProgressBar(self)
        self.progressBar.setRange(0, 0)  # Indeterminate
        layout.addWidget(self.progressBar)
        self.setLayout(layout)
