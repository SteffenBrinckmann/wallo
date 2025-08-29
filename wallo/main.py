""" Main window for the Wallo application, providing a text editor with LLM assistance. """
import sys
from pathlib import Path
from typing import Any
import qtawesome as qta
from PySide6.QtCore import QThread  # pylint: disable=no-name-in-module
from PySide6.QtGui import QAction, QColor, QFont, QKeySequence, QTextCharFormat, QTextCursor # pylint: disable=no-name-in-module
from PySide6.QtWidgets import (QApplication, QComboBox, QFileDialog, QInputDialog, QMainWindow, QMessageBox, # pylint: disable=no-name-in-module
                               QProgressBar, QToolBar, QWidget)
from .busyDialog import BusyDialog
from .configFileManager import ConfigurationManager
from .configMain import ConfigurationWidget
from .docxExport import DocxExporter
from .editor import TextEdit
from .llmProcessor import LLMProcessor
from .pdfDocumentProcessor import PdfDocumentProcessor
from .worker import Worker

progressBarInStatusBar = True  # True to show progress bar in status bar, False for dialog

class Wallo(QMainWindow):
    """ Main window for the Wallo application, providing a text editor with LLM assistance. """
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle('WALLO - Writing Assistance by Large Language mOdel')
        self.editor = TextEdit()
        self.worker: Worker | None = None
        self.subThread: QThread | None = None
        self.progressDialog: BusyDialog | None = None
        self.selectedTextStart: int = 0
        self.selectedTextEnd: int = 0
        self.llmCB     = QComboBox()
        self.serviceCB = QComboBox()
        self.llmSPCB   = QComboBox()
        self.toolbar: 'QToolBar' | None = None
        self.setCentralWidget(self.editor)
        self.statusBar()  # Initialize the status bar
        self.editor.textChanged.connect(self.updateStatusBar)
        self.editor.selectionChanged.connect(self.updateStatusBar)

        # Initialize business logic components
        self.configManager = ConfigurationManager()
        self.llmProcessor = LLMProcessor(self.configManager)
        self.documentProcessor = PdfDocumentProcessor()
        self.configWidget: ConfigurationWidget | None = None
        self.docxExporter = DocxExporter(self)

        self.createToolbar()
        self.updateStatusBar()
        if progressBarInStatusBar:
            # progress bar
            self.progressBar = QProgressBar()
            self.progressBar.setMaximumWidth(200)
            self.progressBar.setVisible(False)
            self.statusBar().addPermanentWidget(self.progressBar)


    def useLLM(self, _:int) -> None:
        """ Use the selected LLM to process the text in the editor
        Args:
            _ (int): The index of the selected item in the combo box.
        """
        cursor = self.editor.textCursor()
        promptName = self.llmCB.currentData()
        serviceName = self.serviceCB.currentText()
        try:
            promptConfig = self.configManager.getPromptByName(promptName)
            if not promptConfig:
                QMessageBox.warning(self, 'Error', f"Prompt '{promptName}' not found")
                return
            attachmentType = promptConfig['attachment']
            if attachmentType == 'selection':
                if not cursor.hasSelection():
                    QMessageBox.information(self, 'Warning', 'You have to select text for the tool to work')
                    return
                selectedText = cursor.selectedText()
                self.selectedTextStart = cursor.selectionStart()
                self.selectedTextEnd = cursor.selectionEnd()
                workParams = self.llmProcessor.processPrompt(promptName, serviceName, selectedText)
                self.runWorker('chatAPI', workParams)
            elif attachmentType == 'pdf':
                res = QFileDialog.getOpenFileName(self, 'Open pdf file', str(Path.home()), '*.pdf')
                if not res or not res[0]:
                    return
                # Validate PDF file
                if not self.documentProcessor.validatePdfFile(res[0]):
                    QMessageBox.warning(self, 'Error', 'Invalid PDF file selected')
                    return
                workParams = self.llmProcessor.processPrompt(promptName, serviceName, res[0])
                self.runWorker('pdfExtraction', workParams)
            elif attachmentType == 'inquiry':
                if not cursor.hasSelection():
                    QMessageBox.information(self, 'Warning', 'You have to select text for the tool to work')
                    return
                inquiryText = self.llmProcessor.getInquiryText(promptName)
                if not inquiryText:
                    QMessageBox.warning(self, 'Error', 'Invalid inquiry prompt configuration')
                    return
                userInput, ok = QInputDialog.getText(self, 'Enter input', f"Please enter {inquiryText}")
                if not ok or not userInput:
                    return
                selectedText = cursor.selectedText()
                self.selectedTextStart = cursor.selectionStart()
                self.selectedTextEnd = cursor.selectionEnd()
                workParams = self.llmProcessor.processPrompt(promptName, serviceName, selectedText, userInput)
                self.runWorker('chatAPI', workParams)
            else:
                QMessageBox.warning(self, 'Error', f"Unknown attachment type: {attachmentType}")
                return
        except ValueError as e:
            QMessageBox.critical(self, 'Configuration Error', str(e))
        except Exception as e:
            QMessageBox.critical(self, 'Error', f"An unexpected error occurred: {str(e)}")


    def useLLMShortcut(self, index: int) -> None:
        """ Use LLM via keyboard shortcut.
        Args:
            index (int): The index of the prompt to use.
        """
        if index < self.llmCB.count():
            self.llmCB.setCurrentIndex(index)
            self.useLLM(index)

    def changeSystemPrompt(self, _: int) -> None:
        """ Change the system prompt used by the LLM.
        Args:
            _ (int): The index of the selected system prompt.
        """
        promptName = self.llmSPCB.currentText()
        try:
            self.llmProcessor.setSystemPrompt(promptName)
        except Exception as e:
            QMessageBox.critical(self, 'Error', f"An unexpected error occurred: {str(e)}")

    def createToolbar(self) -> None:
        """ Create the toolbar with formatting actions and LLM selection"""
        # Remove existing toolbar if present
        if getattr(self, 'toolbar', None):
            try:
                if self.toolbar is not None:
                    self.removeToolBar(self.toolbar)
            except Exception:
                pass
            if self.toolbar is not None:
                self.toolbar.deleteLater()
            self.toolbar = None
        self.toolbar = QToolBar('Main')
        # formats
        self.addToolBar(self.toolbar)
        boldAction = QAction('', self, icon=qta.icon('fa5s.bold'))           # Bold
        boldAction.triggered.connect(self.toggleBold)
        self.toolbar.addAction(boldAction)
        italicAction = QAction('', self, icon=qta.icon('fa5s.italic'))       # Italic
        italicAction.triggered.connect(self.toggleItalic)
        self.toolbar.addAction(italicAction)
        underlineAction = QAction('', self, icon=qta.icon('fa5s.underline')) # Underline
        underlineAction.triggered.connect(self.toggleUnderline)
        self.toolbar.addAction(underlineAction)
        wideSep1 = QWidget()
        wideSep1.setFixedWidth(20)
        self.toolbar.addWidget(wideSep1)
        # save action
        saveAction = QAction('', self, icon=qta.icon('fa5.save'), toolTip='save as docx')# Save as docx
        saveAction.triggered.connect(self.saveDocx)
        self.toolbar.addAction(saveAction)
        wideSep2 = QWidget()
        wideSep2.setFixedWidth(20)
        self.toolbar.addWidget(wideSep2)
        # add LLM selections
        self.toolbar.addSeparator()
        self.llmCB = QComboBox()
        prompts = self.configManager.get('prompts')
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
        self.llmCB.activated.connect(self.useLLM)
        self.toolbar.addWidget(self.llmCB)
        # add system prompt selection
        self.llmSPCB = QComboBox()
        systemPrompts = self.configManager.get('system-prompts')
        for i, prompt in enumerate(systemPrompts):
            self.llmSPCB.addItem(prompt['name'])
        self.llmSPCB.activated.connect(self.changeSystemPrompt)
        self.toolbar.addWidget(self.llmSPCB)
        clearFormatAction = QAction('', self, icon=qta.icon('fa5s.eraser'), toolTip='Clear all formatting',
                                    shortcut=QKeySequence('Ctrl+Space'))
        clearFormatAction.triggered.connect(self.clearFormatting)
        self.toolbar.addAction(clearFormatAction)
        wideSep3 = QWidget()
        wideSep3.setFixedWidth(20)
        self.toolbar.addWidget(wideSep3)
        # add service selection
        self.toolbar.addSeparator()
        self.serviceCB = QComboBox()
        services = self.configManager.get('services')
        if isinstance(services, dict):
            self.serviceCB.addItems(list(services.keys()))
        self.toolbar.addWidget(self.serviceCB)
        configAction = QAction('', self, icon=qta.icon('fa5s.cog'), toolTip='Configuration',
                               shortcut=QKeySequence('Ctrl+0'))
        configAction.triggered.connect(self.showConfiguration)
        self.toolbar.addAction(configAction)


    def toggleBold(self) -> None:
        """ Toggle bold formatting for the selected text or the word under the cursor. """
        fmt = QTextCharFormat()
        fmt.setFontWeight(QFont.Bold if not self.editor.fontWeight() == QFont.Bold else QFont.Normal)# type: ignore[attr-defined]
        self.mergeFormat(fmt)

    def toggleItalic(self) -> None:
        """ Toggle italic formatting for the selected text or the word under the cursor. """
        fmt = QTextCharFormat()
        fmt.setFontItalic(not self.editor.fontItalic())
        self.mergeFormat(fmt)

    def toggleUnderline(self) -> None:
        """ Toggle underline formatting for the selected text or the word under the cursor. """
        fmt = QTextCharFormat()
        fmt.setFontUnderline(not self.editor.fontUnderline())
        self.mergeFormat(fmt)

    def mergeFormat(self, fmt: QTextCharFormat) -> None:
        """ Merge the given character format with the current text cursor.
        Args:
            fmt (QTextCharFormat): The character format to merge.
        """
        cursor = self.editor.textCursor()
        if not cursor.hasSelection():
            cursor.select(QTextCursor.WordUnderCursor)              # type: ignore[attr-defined]
        cursor.mergeCharFormat(fmt)
        self.editor.mergeCurrentCharFormat(fmt)


    def clearFormatting(self) -> None:
        """ Clear all formatting from the entire text in the editor. """
        cursor = self.editor.textCursor()
        cursor.select(QTextCursor.SelectionType.Document)
        defaultFormat = QTextCharFormat()
        cursor.setCharFormat(defaultFormat)
        cursor.clearSelection()


    def saveDocx(self) -> None:
        """ Save the content of the editor as a .docx file."""
        filename, _ = QFileDialog.getSaveFileName(self, 'Save File', '', 'Word Files (*.docx)')
        if filename:
            self.docxExporter.exportToDocx(self.editor, filename)


    def updateStatusBar(self) -> None:
        """ Update the status bar with the current word and character count."""
        text = self.editor.toPlainText()
        message = f"Total: words {len(text.split())}; characters {len(text)}"
        if self.editor.textCursor().hasSelection():
            text = self.editor.textCursor().selectedText()
            message += f"  |  Selection: words {len(text.split())}; characters {len(text)}"
        self.statusBar().showMessage(message)


    def runWorker(self, workType:str, work:dict[str, Any]) -> None:
        """ Run a worker thread to perform the specified work -> keep GUI responsive.
        Args:
            workType (str): The type of work to be performed (e.g., 'chatAPI', 'pdfExtraction').
            work (dict): The work parameters, such as client, model, prompt, and fileName.
        """
        if progressBarInStatusBar:
            self.progressBar.setRange(0, 0)  # Indeterminate/bouncing
            self.progressBar.setVisible(True)
            self.statusBar().showMessage('Working...')
        else:                           # Show progress dialog
            self.progressDialog = BusyDialog(parent=self)
            self.progressDialog.show()
            QApplication.processEvents()  # Ensure dialog is shown
        self.subThread = QThread()
        self.worker = Worker(workType, work)
        self.worker.moveToThread(self.subThread)
        self.subThread.started.connect(self.worker.run)
        self.worker.finished.connect(self.onLLMFinished)
        self.worker.error.connect(self.onLLMError)
        self.worker.finished.connect(self.subThread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.subThread.finished.connect(self.subThread.deleteLater)
        self.subThread.start()


    def onLLMFinished(self, content:str) -> None:
        """ Handle the completion of the LLM worker.
        Args:
            content (str): The content generated by the LLM worker.
        """
        if progressBarInStatusBar:
            self.progressBar.setVisible(False)
        else:
            if self.progressDialog:
                self.progressDialog.close()

        self.statusBar().clearMessage()
        cursor = self.editor.textCursor()

        # Apply blue color to the previously selected text
        if self.selectedTextStart != self.selectedTextEnd:
            cursor.setPosition(self.selectedTextStart)
            cursor.setPosition(self.selectedTextEnd, QTextCursor.MoveMode.KeepAnchor)
            blueFormat = QTextCharFormat()
            blueFormat.setForeground(QColor(self.configManager.get('colorOriginal')))
            cursor.mergeCharFormat(blueFormat)

        # Position cursor at the end for inserting new content
        cursor.setPosition(self.selectedTextEnd)

        # Process the content using the LLM processor
        processContent = self.llmProcessor.processLLMResponse(content)

        # Insert the formatted content with green color HTML styling
        header = self.llmProcessor.configManager.get('header')
        footer = self.llmProcessor.configManager.get('footer')

        # Wrap the content in green color HTML span
        replyColor = QColor(self.configManager.get('colorReply')).getRgb()[:3] # type: ignore[index]
        styledContent = f'<span style="color: rgb{replyColor};">{processContent}</span>'
        fullContent = f"<br>{header}{styledContent}{footer}<br>"
        cursor.insertHtml(fullContent)


    def onLLMError(self, errorMsg:str) -> None:
        """ Handle errors from the LLM worker.
        Args:
            errorMsg (str): The error message from the worker.
        """
        if progressBarInStatusBar:
            self.progressBar.setVisible(False)
        else:
            if self.progressDialog:
                self.progressDialog.close()
        self.statusBar().clearMessage()
        QMessageBox.critical(self, 'Worker Error', errorMsg)


    def showConfiguration(self) -> None:
        """Show the configuration widget."""
        if self.configWidget is None:
            self.configWidget = ConfigurationWidget(self.configManager)
            self.configWidget.configChanged.connect(self.onConfigChanged)
        self.configWidget.show()
        self.configWidget.raise_()
        self.configWidget.activateWindow()


    def onConfigChanged(self) -> None:
        """Handle configuration changes."""
        # Reload the toolbar to reflect changes
        self.createToolbar()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = Wallo()
    win.resize(1024, 800)
    win.show()
    sys.exit(app.exec())
