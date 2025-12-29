""" Worker class to handle background tasks such as LLM processing or PDF extraction."""
from typing import Any
from PySide6.QtCore import QObject, Signal  # pylint: disable=no-name-in-module
from .pdfDocumentProcessor import PdfDocumentProcessor

DEBUG_MODE = False  # Set to True to enable debug mode that skips actual LLM calls

class Worker(QObject):
    """ Worker class to handle background tasks such as LLM processing or PDF extraction.
    Attention: this class is recreated for each work request, there is no persistence.
    """
    finished = Signal(str,str,str)  # Content and previous-prompt ID, senderID
    error = Signal(str,str)         # Error message, senderID

    def __init__(self, workType:str, objects:dict[str, Any]) -> None:
        """ Initialize the Worker with the type of work and necessary objects.
        Args:
            workType (str): The type of work to be performed (e.g., 'chatAPI', 'pdfExtraction').
            objects (dict): A dictionary containing the necessary objects for the work, such as
                client, model, prompt, and fileName.
        """
        super().__init__()
        self.workType              = workType
        self.senderID              = objects['senderID']
        self.client                = objects['client']
        self.model                 = objects['model']
        self.prompt                = objects['prompt']
        self.systemPrompt          = objects.get('systemPrompt','You are a helpful assistant.')
        self.fileName              = objects.get('fileName','')
        self.previousPromptId      = objects.get('previousPromptId','')
        self.documentProcessor     = PdfDocumentProcessor()


    def run(self) -> None:
        """ Run the worker based on the specified work type. """
        try:
            extractedContent = ''
            if self.workType == 'pdfExtraction':
                extractedContent = self.documentProcessor.extractTextFromPdf(self.fileName)
            userContent = f"{self.prompt}{extractedContent}"
            messages = [{'role': 'system', 'content': self.systemPrompt},
                        {'role': 'user', 'content': userContent}]
            print('start api request')
            if self.previousPromptId:
                response = self.client.responses.create(model=self.model, input=messages,
                                                            previous_response_id=self.previousPromptId)
            else:
                response = self.client.responses.create(model=self.model, input=messages)
            print('api request done')
            content = [i.content[0].text for i in response.output
                        if hasattr(i, 'content') and i.content is not None][0]
            responseID = response.id
            self.finished.emit(content, responseID, self.senderID)
        except Exception as e:
            self.error.emit(str(e), self.senderID)
