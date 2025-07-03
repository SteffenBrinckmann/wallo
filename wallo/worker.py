from typing import Any
from PySide6.QtCore import Signal, QObject
import pdfplumber

class Worker(QObject):
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, workType:str, objects:dict[str, Any]):
        """ Initialize the Worker with the type of work and necessary objects.
        Args:
            workType (str): The type of work to be performed (e.g., 'chatAPI', 'pdfExtraction').
            objects (dict): A dictionary containing the necessary objects for the work, such as client, model, prompt, and fileName.
        """
        super().__init__()
        self.workType = workType
        self.client   = objects['client']
        self.model    = objects['model']
        self.prompt   = objects['prompt']
        self.fileName = objects.get('fileName','')


    def run(self):
        """ Run the worker based on the specified work type."""
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

