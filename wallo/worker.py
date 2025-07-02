from PySide6.QtCore import Signal, QObject
import pdfplumber

class Worker(QObject):
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, workType, objects):
        super().__init__()
        self.workType = workType
        self.client   = objects['client']
        self.model    = objects['model']
        self.prompt   = objects['prompt']
        self.fileName = objects.get('fileName','')


    def run(self):
        try:
            content = ''
            # Work before LLM
            if self.workType == 'pdfExtraction':
                with pdfplumber.open(self.fileName) as pdf:
                    content = "\n".join(page.extract_text() or "" for page in pdf.pages)
                if not content.strip():
                    raise ValueError("PDF Error: No text found in the PDF.")
            # LLM work
            messages = [{'role': 'system', 'content': 'You are a helpful assistant.'},
                        {'role': 'user', 'content': self.prompt+content}]
            response = self.client.chat.completions.create(model=self.model, messages=messages)
            content = response.choices[0].message.content.strip()
            self.finished.emit(content)
        except Exception as e:
            self.error.emit(str(e))

