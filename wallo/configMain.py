"""Configuration widget for managing application settings."""
from typing import Any, Optional
from PySide6.QtCore import Signal  # pylint: disable=no-name-in-module
from PySide6.QtGui import QKeyEvent  # pylint: disable=no-name-in-module
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QTabWidget, QTextEdit, QVBoxLayout, QWidget # pylint: disable=no-name-in-module
from .configManager import ConfigurationManager
from .configTabProfile import ProfileTab
from .configTabServices import ServiceTab
from .configTabString import StringTab
from .misc import HELP_TEXT


class ConfigurationWidget(QWidget):
    """Main configuration widget with tabs."""
    configChanged = Signal()

    def __init__(self, configManager: ConfigurationManager, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.configManager = configManager
        self.setWindowTitle('Configuration')
        self.resize(800, 600)

        layout = QVBoxLayout(self)
        self.tabWidget = QTabWidget()
        self.profileTab = ProfileTab(self.configManager)
        self.serviceTab = ServiceTab(self.configManager)
        self.stringTab = StringTab(self.configManager)
        self.helpTab = Help()
        self.tabWidget.addTab(self.profileTab, 'Profiles')
        self.tabWidget.addTab(self.serviceTab, 'Services')
        self.tabWidget.addTab(self.stringTab, 'Interface')
        self.tabWidget.addTab(self.helpTab, 'Help')
        layout.addWidget(self.tabWidget)

        # Close button
        buttonLayout = QHBoxLayout()
        buttonLayout.addStretch()
        self.closeBtn = QPushButton('Close')
        self.closeBtn.clicked.connect(self.close)
        buttonLayout.addWidget(self.closeBtn)
        layout.addLayout(buttonLayout)


    def keyPressEvent(self, event:QKeyEvent) -> None:
        """Handle key press events.
        Args:
            event: The key event.
        """
        if event.key() == 0x01000000:  # Qt.Key_Escape
            self.close()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event: Any) -> None:
        """Handle close event."""
        self.configChanged.emit()
        super().closeEvent(event)


class Help(QWidget):
    """Tab for showing the help text."""
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.mainLayout = QVBoxLayout(self)
        text = QTextEdit()
        text.setMarkdown(HELP_TEXT)
        text.setReadOnly(True)
        self.mainLayout.addWidget(text)
