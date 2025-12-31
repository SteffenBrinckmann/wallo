"""Tab for managing string configurations."""
from typing import Optional
try:
    import enchant
    import pycountry
    ENCHANT_AVAILABLE = True
except ImportError:
    ENCHANT_AVAILABLE = False
from PySide6.QtGui import QColor  # pylint: disable=no-name-in-module
from PySide6.QtWidgets import (QColorDialog, QFormLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, # pylint: disable=no-name-in-module
                               QWidget, QComboBox)
from .configFileManager import ConfigurationManager


class StringTab(QWidget):
    """Tab for managing string configurations."""

    def __init__(self, configManager: ConfigurationManager, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.configManager = configManager
        self.setupUI()
        self.loadStrings()


    def setupUI(self) -> None:
        """Setup the tab UI."""
        layout = QVBoxLayout(self)
        formLayout = QFormLayout()

        self.colorLabel1 = QLabel()
        self.colorLabel1.setFixedWidth(30)
        self.colorLabel1.setFixedHeight(30)
        self.colorLabel1.setAutoFillBackground(True)
        self.colorBtn1 = QPushButton('Choose original text color')
        self.colorBtn1.clicked.connect(lambda: self.chooseColor('Original'))
        colorLayout1 = QHBoxLayout()
        colorLayout1.addWidget(self.colorBtn1)
        colorLayout1.addWidget(self.colorLabel1)
        formLayout.addRow('Original text Color:', colorLayout1)

        if ENCHANT_AVAILABLE:
            self.cbLanguages = QComboBox()
            for code in enchant.list_languages():
                parts = code.split('_')
                lang = pycountry.languages.get(alpha_2=parts[0])
                country = pycountry.countries.get(alpha_2=parts[1]) if len(parts) > 1 else None
                self.cbLanguages.addItem(f"{lang.name} ({country.name})" if country else lang.name if lang else code,
                                         userData=code)
            formLayout.addRow('Dictionary:', self.cbLanguages)

        formLayout.addRow('', QLabel(''))
        layout.addLayout(formLayout)
        buttonLayout = QHBoxLayout()
        self.saveBtn = QPushButton('Save Changes')
        self.saveBtn.clicked.connect(self.saveStrings)
        buttonLayout.addWidget(self.saveBtn)
        buttonLayout.addStretch()
        layout.addLayout(buttonLayout)
        layout.addStretch()

    def chooseColor(self, key: str) -> None:
        """Open color dialog to choose a color."""
        currentColor = self.configManager.get(f'color{key}')
        color = QColorDialog.getColor(QColor(currentColor), self, 'Select Color')
        if color.isValid():
            colorHex = color.name()
            self.configManager.updateConfig({f'color{key}': colorHex})
            self.updateColorLabel()

    def updateColorLabel(self) -> None:
        """Update color labels to show current colors."""
        color1 = self.configManager.get('colorOriginal')
        palette1 = self.colorLabel1.palette()
        palette1.setColor(self.colorLabel1.backgroundRole(), color1)
        self.colorLabel1.setPalette(palette1)


    def loadStrings(self) -> None:
        """Load string configurations."""
        self.cbLanguages.setCurrentIndex(self.cbLanguages.findData(self.configManager.get('dictionary')))


    def saveStrings(self) -> None:
        """Save string configurations."""
        updates = {
            'dictionary': self.cbLanguages.currentData() if ENCHANT_AVAILABLE else '',
        }
        self.configManager.updateConfig(updates)
