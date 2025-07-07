""" Main window for the Wallo application, providing a text editor with LLM assistance. """
import sys, json
from typing import Any
from pathlib import Path
from PySide6.QtWidgets import (QApplication, QMainWindow, QToolBar, QFileDialog, QMessageBox, QComboBox, # pylint: disable=no-name-in-module
                               QProgressBar, QInputDialog)
from PySide6.QtGui import QTextCursor, QTextCharFormat, QFont, QAction     # pylint: disable=no-name-in-module
from PySide6.QtCore import QThread                                         # pylint: disable=no-name-in-module
import qtawesome as qta
# import pypandoc
from openai import OpenAI
from .fixedStrings import defaultConfiguration, progressbarInStatusbar, header, footer, defaultPromptFooter
from .editor import TextEdit
from .worker import Worker
from .busyDialog import BusyDialog


class Wallo(QMainWindow):
    """ Main window for the Wallo application, providing a text editor with LLM assistance. """
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("WALLO - Writing Assistance by Large Language mOdel")
        self.editor = TextEdit()
        self.worker: Worker | None = None
        self.subThread: QThread | None = None
        self.progressDialog: BusyDialog | None = None
        self.setCentralWidget(self.editor)
        self.statusBar()  # Initialize the status bar
        self.editor.textChanged.connect(self.updateStatusBar)
        self.editor.selectionChanged.connect(self.updateStatusBar)
        self.configFile = Path.home()/'.wallo.json'
        if not self.configFile.is_file():
            with open(self.configFile, 'w', encoding='utf-8') as confFile:
                confFile.write(json.dumps(defaultConfiguration, indent=2))
        self.createToolbar()
        self.updateStatusBar()
        if progressbarInStatusbar:
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
        with open(self.configFile, 'r', encoding='utf-8') as fIn:
            conf = json.load(fIn)
        promptFooter = conf.get('promptFooter', defaultPromptFooter)
        service = conf['services'][self.serviceCB.currentText()]
        client = OpenAI(api_key=service['api'], base_url=service['url'])
        confPrompt = [i for i in conf['prompts'] if i['name']==self.llmCB.currentData()][0]

        if confPrompt['attachment'] == 'selection':
            if not cursor.hasSelection():
                QMessageBox.information(self, "Warning", "You have to select text for the tool to work")
                return
            prompt = confPrompt['user-prompt'] + '\n' + self.editor.textCursor().selectedText() + promptFooter
            print(prompt)
            self.runWorker('chatAPI', {'client':client, 'model':service['model'], 'prompt':prompt})

        elif confPrompt['attachment'] == 'pdf':
            res = QFileDialog.getOpenFileName(self, "Open pdf file", str(Path.home()), '*.pdf')
            if not res or not res[0]:
                return
            prompt = confPrompt['user-prompt']+ promptFooter+'\n'
            print(prompt)
            self.runWorker('pdfExtraction', {'client':client, 'model':service['model'],'prompt':prompt,
                                             'fileName':res[0]})

        elif confPrompt['attachment'] == 'inquiry':
            if not cursor.hasSelection():
                QMessageBox.information(self, "Warning", "You have to select text for the tool to work")
                return
            inquiryText = confPrompt['user-prompt'].split('|')[1]
            text, ok = QInputDialog.getText(self, "Enter number", f"Please enter {inquiryText}")
            if ok and text:
                prompt = confPrompt['user-prompt'].replace('|'+inquiryText+'|',text) + '\n\n' + \
                         self.editor.textCursor().selectedText() +'\n'+promptFooter
            print(prompt)
            self.runWorker('chatAPI', {'client':client, 'model':service['model'], 'prompt':prompt})

        else:
            print('ERROR unknown attachment')
            return
        return



    def createToolbar(self) -> None:
        """ Create the toolbar with formatting actions and LLM selection"""
        toolbar = QToolBar("Formatting")
        self.addToolBar(toolbar)
        boldAction = QAction('', self, icon=qta.icon('fa5s.bold'))           # Bold
        boldAction.triggered.connect(self.toggleBold)
        toolbar.addAction(boldAction)
        italicAction = QAction('', self, icon=qta.icon('fa5s.italic'))       # Italic
        italicAction.triggered.connect(self.toggleItalic)
        toolbar.addAction(italicAction)
        underlineAction = QAction('', self, icon=qta.icon('fa5s.underline')) # Underline
        underlineAction.triggered.connect(self.toggleUnderline)
        toolbar.addAction(underlineAction)
        saveAction = QAction('', self, icon=qta.icon('fa5.save'), toolTip='save as docx')# Save as docx
        saveAction.triggered.connect(self.saveDocx)
        toolbar.addAction(saveAction)
        # add LLM selections
        toolbar.addSeparator()
        with open(self.configFile, 'r', encoding='utf-8') as fIn:
            prompts = json.load(fIn)['prompts']
        self.llmCB = QComboBox()
        for i in prompts:
            self.llmCB.addItem(i['description'], i['name'])
        self.llmCB.activated.connect(self.useLLM)
        toolbar.addWidget(self.llmCB)
        # add service selection
        toolbar.addSeparator()
        with open(self.configFile, 'r', encoding='utf-8') as fIn:
            services = json.load(fIn)['services']
        self.serviceCB = QComboBox()
        self.serviceCB.addItems([k for k,_ in services.items()])
        toolbar.addWidget(self.serviceCB)


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

    def saveDocx(self) -> None:
        """ Save the content of the editor as a .docx file."""
        filename, _ = QFileDialog.getSaveFileName(self, "Save File", "", "Word Files (*.docx)")
        if filename:
            html = self.editor.toHtml()
            print(html)
            # Does not conserve format
            # pypandoc.download_pandoc()
            # pypandoc.convert_text(html, 'docx', format='html', outputfile=filename)


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
        if progressbarInStatusbar:
            self.progressBar.setRange(0, 0)  # Indeterminate/bouncing
            self.progressBar.setVisible(True)
            self.statusBar().showMessage("Working...")
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
        if progressbarInStatusbar:
            self.progressBar.setVisible(False)
        else:
            self.progressDialog.close()
        self.statusBar().clearMessage()
        cursor = self.editor.textCursor()
        cursor.setPosition(cursor.selectionEnd())
        content = content.strip()
        if content.endswith('```'):
            content = content[:-3].strip()
        if content.startswith('```'):
            content = content.split('\n', 1)[-1].strip()
        cursor.insertHtml(f'{header}\n{content}{footer}\n')

    def onLLMError(self, errorMsg:str) -> None:
        """ Handle errors from the LLM worker.
        Args:
            errorMsg (str): The error message from the worker.
        """
        if progressbarInStatusbar:
            self.progressBar.setVisible(False)
        else:
            self.progressDialog.close()
        self.statusBar().clearMessage()
        QMessageBox.critical(self, "Worker Error", errorMsg)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = Wallo()
    win.resize(800, 600)
    win.show()
    sys.exit(app.exec())
