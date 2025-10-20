"""Tab for managing string configurations."""
from typing import Optional
try:
    import enchant
    import pycountry
    ENCHANT_AVAILABLE = True
except ImportError:
    ENCHANT_AVAILABLE = False
from PySide6.QtGui import QColor  # pylint: disable=no-name-in-module
from PySide6.QtWidgets import (QColorDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, # pylint: disable=no-name-in-module
                               QTextEdit, QVBoxLayout, QWidget, QComboBox)
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

        self.colorLabel2 = QLabel()
        self.colorLabel2.setFixedWidth(30)
        self.colorLabel2.setFixedHeight(30)
        self.colorLabel2.setAutoFillBackground(True)
        self.colorBtn2 = QPushButton('Choose reply text color')
        self.colorBtn2.clicked.connect(lambda: self.chooseColor('Reply'))
        colorLayout2 = QHBoxLayout()
        colorLayout2.addWidget(self.colorBtn2)
        colorLayout2.addWidget(self.colorLabel2)
        formLayout.addRow('Reply text Color:', colorLayout2)
        self.updateColorLabel()

        self.headerEdit = QLineEdit()
        formLayout.addRow('Header:', self.headerEdit)
        self.footerEdit = QLineEdit()
        formLayout.addRow('Footer:', self.footerEdit)
        self.promptFooterEdit = QTextEdit()
        self.promptFooterEdit.setMaximumHeight(100)
        formLayout.addRow('Prompt Footer:', self.promptFooterEdit)

        if ENCHANT_AVAILABLE:
            self.cbLanguages = QComboBox()
            for code in enchant.list_languages():
                parts = code.split('_')
                lang = pycountry.languages.get(alpha_2=parts[0])
                country = pycountry.countries.get(alpha_2=parts[1]) if len(parts) > 1 else None
                self.cbLanguages.addItem(f"{lang.name} ({country.name})" if country else lang.name if lang else code,
                                         userData=code)
            formLayout.addRow('Dictionary:', self.cbLanguages)

        formLayout.addRow('Shortcuts:', QLabel(''))
        self.scIdea = QLineEdit()
        formLayout.addRow('Ideazing mode:', self.scIdea)
        self.scReduce = QLineEdit()
        formLayout.addRow('Reduce to highlighted text:', self.scReduce)
        self.scDelete = QLineEdit()
        formLayout.addRow('Delete block:', self.scDelete)
        self.scClear = QLineEdit()
        formLayout.addRow('Clear all formatting:', self.scClear)
        self.scConfig = QLineEdit()
        formLayout.addRow('Open configuration:', self.scConfig)
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

        color2 = self.configManager.get('colorReply')
        palette2 = self.colorLabel2.palette()
        palette2.setColor(self.colorLabel2.backgroundRole(), color2)
        self.colorLabel2.setPalette(palette2)


    def loadStrings(self) -> None:
        """Load string configurations."""
        self.headerEdit.setText(self.configManager.get('header'))
        self.footerEdit.setText(self.configManager.get('footer'))
        self.promptFooterEdit.setPlainText(self.configManager.get('promptFooter'))
        self.scIdea.setText(self.configManager.get('shortcuts')['Ideazing mode'])
        self.scReduce.setText(self.configManager.get('shortcuts')['Reduce to highlighted text'])
        self.scDelete.setText(self.configManager.get('shortcuts')['Remove block'])
        self.scClear.setText(self.configManager.get('shortcuts')['Clear all formatting'])
        self.scConfig.setText(self.configManager.get('shortcuts')['Configuration'])
        self.cbLanguages.setCurrentIndex(self.cbLanguages.findData(self.configManager.get('dictionary')))


    def saveStrings(self) -> None:
        """Save string configurations."""
        updates = {
            'header': self.headerEdit.text(),
            'footer': self.footerEdit.text(),
            'promptFooter': self.promptFooterEdit.toPlainText(),
            'dictionary': self.cbLanguages.currentData() if ENCHANT_AVAILABLE else '',
            'shortcuts': {
                'Ideazing mode': self.scIdea.text(),
                'Reduce to highlighted text': self.scReduce.text(),
                'Remove block': self.scDelete.text(),
                'Clear all formatting': self.scClear.text(),
                'Configuration': self.scConfig.text()
            }
        }
        self.configManager.updateConfig(updates)
