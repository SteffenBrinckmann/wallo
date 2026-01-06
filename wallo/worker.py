""" Worker class to handle background tasks such as LLM processing or PDF extraction."""
from typing import Any
from langchain_core.messages import SystemMessage
from langchain_core.documents.base import Blob
from PySide6.QtCore import QObject, Signal  # pylint: disable=no-name-in-module
from .pdfDocumentProcessor import PdfDocumentProcessor

DEBUG_MODE = True  # Set to True to enable debug mode that skips actual LLM calls

class Worker(QObject):
    """ Worker class to handle background tasks such as LLM processing or PDF extraction.
    Attention: this class is recreated for each work request, there is no persistence.
    """
    finished = Signal(str,str,str)  # Content and previous-prompt ID, senderID, workType
    error = Signal(str,str,str)     # Error message, senderID, workType

    def __init__(self, workType:str, objects:dict[str, Any]) -> None:
        """ Initialize the Worker with the type of work and necessary objects.
        Args:
            workType (str): The type of work to be performed (e.g., 'chatAPI', 'pdfExtraction').
            objects (dict): A dictionary containing the necessary objects for the work, such as
                client, model, prompt, and fileName.
        """
        super().__init__()
        self.workType              = workType
        self.objects               = objects
        self.senderID              = self.objects['senderID']
        self.documentProcessor     = PdfDocumentProcessor()


    def run(self) -> None:
        """ Run the worker based on the specified work type. """
        try:
            if self.workType == 'chatAPI':
                # LLM
                runnable         = self.objects['runnable']
                prompt           = self.objects['prompt']
                selectedText     = self.objects['selectedText']
                pdfFilePath      = self.objects['pdfFilePath']
                systemPrompt     = self.objects.get('systemPrompt','You are a helpful assistant.')
                # RAG retrieval
                ragContext = ''
                if self.objects['ragRunnable'] is not None:
                    if retrieved:= self.objects['ragRunnable'].retrieve(selectedText or prompt): #get list of strings from RAG database
                        if DEBUG_MODE:
                            print('RAG context:', '\n\n'.join(retrieved))
                        ragContext = f"\n\nContext:\n---\n{'\n\n'.join(retrieved)}\n---\n"
                # PDF retrieval
                pdfContext = ''
                if pdfFilePath:
                    pdfContext = self.documentProcessor.extractTextFromPdf(pdfFilePath)+'\n\n'

                prompt = f"{prompt}{ragContext}{pdfContext}{selectedText}"
                if DEBUG_MODE:
                    print(f'Start LLM work:\n  {prompt}')
                if not getattr(runnable, 'systemPromptInjected', False):
                    try:
                        runnable.get_history('global').add_message(SystemMessage(content=systemPrompt))
                        runnable.systemPromptInjected = True
                    except Exception:
                        pass
                result = runnable.invoke(prompt, {'configurable': {'session_id': 'global'}})
                content = result.content if hasattr(result, 'content') else str(result)
                if DEBUG_MODE:
                    print(f'End work: {self.senderID}\n  {content}')
                self.finished.emit(content, self.senderID, self.workType)


            if self.workType == 'transcribeAudio':
                runnable         = self.objects['runnable']
                blob = Blob.from_path(self.objects['path'])
                docs = runnable.parse(blob)
                content = ''
                if docs:
                    content = docs[0].page_content
                self.finished.emit(content, self.senderID, self.workType)


            if self.workType == 'ingestRAG':
                runnable  = self.objects['runnable']
                filePaths = self.objects['filePaths']
                chunks    = runnable.ingestPaths(filePaths)
                self.finished.emit(f'Success | Chunks indexed: {chunks}', self.senderID, self.workType)

        except Exception as e:
            self.error.emit(str(e), self.senderID, self.workType)
