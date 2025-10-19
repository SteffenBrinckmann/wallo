""" Worker class to handle background tasks such as LLM processing or PDF extraction."""
from typing import Any
from PySide6.QtCore import QObject, Signal  # pylint: disable=no-name-in-module
from .pdfDocumentProcessor import PdfDocumentProcessor

class Worker(QObject):
    """ Worker class to handle background tasks such as LLM processing or PDF extraction.
    Attention: this class is recreated for each work request, there is no persistence.
    """
    finished = Signal(str,str)  # Content and previous-prompt ID
    error = Signal(str)         # Error message

    def __init__(self, workType:str, objects:dict[str, Any]) -> None:
        """ Initialize the Worker with the type of work and necessary objects.
        Args:
            workType (str): The type of work to be performed (e.g., 'chatAPI', 'pdfExtraction').
            objects (dict): A dictionary containing the necessary objects for the work, such as
                client, model, prompt, and fileName.
        """
        super().__init__()
        self.workType              = workType
        self.client                = objects['client']
        self.model                 = objects['model']
        self.prompt                = objects['prompt']
        self.systemPrompt          = objects.get('systemPrompt','You are a helpful assistant.')
        self.fileName              = objects.get('fileName','')
        self.previousPromptId      = objects.get('previousPromptId','')
        self.documentProcessor = PdfDocumentProcessor()


    def run(self) -> None:
        """ Run the worker based on the specified work type."""
        try:
            content = ''
            if self.workType == 'ideazingChat':
                messages = [{'role': 'system', 'content': self.systemPrompt},
                            {'role': 'user', 'content': self.prompt}]
                if False: # fast debug mode
                    self.finished.emit("Debug mode: conversation completed.", "---")
                    return
                if self.previousPromptId:
                    response = self.client.responses.create(model=self.model, input=messages,
                                                            previous_response_id=self.previousPromptId)
                else:
                    response = self.client.responses.create(model=self.model, input=messages)
                content = [i.content[0].text for i in response.output if hasattr(i, 'content') and i.content is not None][0]
                self.finished.emit(content, response.id)
            else:
                # Work before LLM
                if self.workType == 'pdfExtraction':
                    content = self.documentProcessor.extractTextFromPdf(self.fileName)
                # LLM work
                messages = [{'role': 'system', 'content': self.systemPrompt},
                            {'role': 'user', 'content': self.prompt+content}]
                response = self.client.chat.completions.create(model=self.model, messages=messages)
                content = response.choices[0].message.content.strip()
                self.finished.emit(content, '')
        except Exception as e:
            self.error.emit(str(e))
