"""Shared background worker for non-chat capabilities."""
from typing import Any
from langchain_core.documents.base import Blob
from PySide6.QtCore import QObject, Signal  # pylint: disable=no-name-in-module
from openai import OpenAI


class Worker(QObject):
    """Run STT, RAG ingestion, and TTS outside the GUI thread."""
    finished = Signal(str, str, str)
    error = Signal(str, str, str)

    def __init__(self, workType: str, objects: dict[str, Any]) -> None:
        """Initialize a capability worker.

        Args:
            workType: Capability name to execute.
            objects: Inputs required by the selected capability.
        """
        super().__init__()
        self.workType = workType
        self.objects = objects
        self.senderID = objects['senderID']


    def run(self) -> None:
        """Execute the configured capability and emit its result.
        """
        try:
            handler = {'transcribeAudio': self._runTranscribeAudio, 'ingestRAG': self._runIngestRag,
                       'tts': self._runTts}.get(self.workType)
            if handler is None:
                self.error.emit('Unknown work type', self.senderID, self.workType)
                return
            handler()
        except Exception as error:
            self.error.emit(str(error), self.senderID, self.workType)


    def _runTranscribeAudio(self) -> None:
        """Transcribe an audio file and emit the text.
        """
        docs = self.objects['runnable'].parse(Blob.from_path(self.objects['path']))
        self.finished.emit(docs[0].page_content if docs else '', self.senderID, self.workType)


    def _runIngestRag(self) -> None:
        """Index configured RAG source paths and emit the chunk count.
        """
        chunks = self.objects['runnable'].ingestPaths(self.objects['filePaths'])
        self.finished.emit(f'Success | Chunks indexed: {chunks}', self.senderID, self.workType)


    def _runTts(self) -> None:
        """Generate speech audio and write it to the requested file.
        """
        response = OpenAI(api_key=self.objects['apiKey']).audio.speech.create(
            model='gpt-4o-mini-tts', voice='alloy', input=self.objects['content'])
        with open(self.objects['filePaths'], 'wb') as fileHandle:
            fileHandle.write(response.read())
        self.finished.emit('', self.senderID, self.workType)
