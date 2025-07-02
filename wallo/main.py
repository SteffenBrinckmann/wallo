import sys, json
from pathlib import Path
from PySide6.QtWidgets import QApplication, QMainWindow, QToolBar, QFileDialog, QMessageBox, QComboBox, QFileDialog
from PySide6.QtGui import QTextCursor, QTextCharFormat, QFont, QAction
import qtawesome as qta
import pdfplumber
import pypandoc
from openai import OpenAI
from .fixedStrings import defaultConfiguration
from .editor import TextEdit


class Wallo(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("WALLO - Writing Assistance by Large Language mOdel")
        self.editor = TextEdit()
        self.setCentralWidget(self.editor)
        self.statusBar()  # Initialize the status bar
        self.editor.textChanged.connect(self.updateStatusBar)
        self.editor.selectionChanged.connect(self.updateStatusBar)
        self.configFile = Path.home()/'.wallo.json'
        if not self.configFile.is_file():
            with open(self.configFile, 'w', encoding='utf-8') as confFile:
                confFile.write(json.dumps(defaultConfiguration, indent=2))
        self._create_toolbar()
        self.updateStatusBar()

    def _create_toolbar(self):
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
        toolbar.addSeparator()
        prompts = json.load(open(self.configFile, 'r', encoding='utf-8'))['prompts']
        self.llmCB = QComboBox()
        for i in prompts:
            self.llmCB.addItem(i['description'], i['name'])
        self.llmCB.activated.connect(self.useLLM)
        toolbar.addWidget(self.llmCB)

    def useLLM(self, _):
        """use llm
        Args:
            _ (int): index
        """
        cursor = self.editor.textCursor()
        conf = json.load(open(self.configFile, 'r', encoding='utf-8'))
        service = conf['services']['openAI']
        client = OpenAI(api_key=service['api'], base_url=service['url'])
        confPrompt = [i for i in conf['prompts'] if i['name']==self.llmCB.currentData()][0]
        print('LLM: Create prompt') #TODO add progress-bar
        if confPrompt['attachment'] == 'selection':
            if not cursor.hasSelection():
                QMessageBox.information(self, "Warning", "You have to select text for the tool to work")
                return
            prompt = confPrompt['user-prompt'] + '\n' + self.editor.textCursor().selectedText()
        if confPrompt['attachment'] == 'pdf':
            res = QFileDialog.getOpenFileName(self, "Open pdf file", str(Path.home()), '*.pdf')
            if res is None:
                return
            with pdfplumber.open(res[0]) as pdf:  #TODO chunking
                text = "\n".join(page.extract_text() or "" for page in pdf.pages)
            if not text.strip():
                QMessageBox.warning(self, "PDF Error", "No text found in the PDF.")
                return
            prompt = confPrompt['user-prompt'] + '\n' + text
        print('LLM: ask remote service')
        messages =  [{'role':'system', 'content': 'You are a helpful assistant.'},{'role': 'user', 'content': prompt}]
        response = client.chat.completions.create(model=service['model'], messages=messages)
        print('LLM: got response')
        cursor.setPosition(cursor.selectionEnd())
        cursor.insertText(f'\n{"-"*10}Start LLM generated\n{response.choices[0].message.content.strip()}\n{"-"*10}End LLM generated\n')
        return


    def toggleBold(self):
        fmt = QTextCharFormat()
        fmt.setFontWeight(QFont.Bold if not self.editor.fontWeight() == QFont.Bold else QFont.Normal)
        self.mergeFormat(fmt)

    def toggleItalic(self):
        fmt = QTextCharFormat()
        fmt.setFontItalic(not self.editor.fontItalic())
        self.mergeFormat(fmt)

    def toggleUnderline(self):
        fmt = QTextCharFormat()
        fmt.setFontUnderline(not self.editor.fontUnderline())
        self.mergeFormat(fmt)

    def mergeFormat(self, fmt: QTextCharFormat):
        cursor = self.editor.textCursor()
        if not cursor.hasSelection():
            cursor.select(QTextCursor.WordUnderCursor)
        cursor.mergeCharFormat(fmt)
        self.editor.mergeCurrentCharFormat(fmt)

    def saveDocx(self):
        filename, _ = QFileDialog.getSaveFileName(self, "Save File", "", "Word Files (*.docx)")
        if filename:
            html = self.editor.toHtml()
            print(html)
            # Does not conserve format
            # pypandoc.download_pandoc()
            # pypandoc.convert_text(html, 'docx', format='html', outputfile=filename)

    def _add_runs_with_formatting(self, docx_paragraph, html_element):
        for elem in html_element.descendants:
            if isinstance(elem, str):
                docx_paragraph.add_run(elem)
            elif elem.name in ['b', 'strong']:
                run = docx_paragraph.add_run(elem.get_text())
                run.bold = True
            elif elem.name in ['i', 'em']:
                run = docx_paragraph.add_run(elem.get_text())
                run.italic = True
            elif elem.name == 'u':
                run = docx_paragraph.add_run(elem.get_text())
                run.underline = True

    def updateStatusBar(self):
        text = self.editor.toPlainText()
        message = f"Total: words {len(text.split())}; characters {len(text)}"
        if self.editor.textCursor().hasSelection():
            text = self.editor.textCursor().selectedText()
            message += f"  |  Selection: words {len(text.split())}; characters {len(text)}"
        self.statusBar().showMessage(message)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = Wallo()
    win.resize(800, 600)
    win.show()
    sys.exit(app.exec())
