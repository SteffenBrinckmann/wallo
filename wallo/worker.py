""" Worker class to handle background tasks such as LLM processing or PDF extraction."""
from typing import Any
from PySide6.QtCore import Signal, QObject  # pylint: disable=no-name-in-module
from .pdfDocumentProcessor import PdfDocumentProcessor

class Worker(QObject):
    """ Worker class to handle background tasks such as LLM processing or PDF extraction."""
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, workType:str, objects:dict[str, Any]) -> None:
        """ Initialize the Worker with the type of work and necessary objects.
        Args:
            workType (str): The type of work to be performed (e.g., 'chatAPI', 'pdfExtraction').
            objects (dict): A dictionary containing the necessary objects for the work, such as
                client, model, prompt, and fileName.
        """
        super().__init__()
        self.workType = workType
        self.client   = objects['client']
        self.model    = objects['model']
        self.prompt   = objects['prompt']
        self.fileName = objects.get('fileName','')
        self.documentProcessor = PdfDocumentProcessor()


    def run(self) -> None:
        """ Run the worker based on the specified work type."""
        try:
            content = ''
            # Work before LLM
            if self.workType == 'pdfExtraction':
                content = self.documentProcessor.extractTextFromPdf(self.fileName)
            # LLM work
            messages = [{'role': 'system', 'content': 'You are a helpful assistant.'},
                        {'role': 'user', 'content': self.prompt+content}]
            response = self.client.chat.completions.create(model=self.model, messages=messages)
            content = response.choices[0].message.content.strip()
            self.finished.emit(content)
        except Exception as e:
            self.error.emit(str(e))
