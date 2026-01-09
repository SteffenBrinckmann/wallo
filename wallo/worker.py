""" Worker class to handle background tasks such as LLM processing or PDF extraction."""
from typing import Any
from langchain_core.messages import HumanMessage, ToolMessage
from langchain_core.documents.base import Blob
from PySide6.QtCore import QObject, Signal  # pylint: disable=no-name-in-module
from openai import OpenAI
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
            handler = {
                'chatAPI': self._run_chat_api,
                'transcribeAudio': self._run_transcribe_audio,
                'ingestRAG': self._run_ingest_rag,
                'tts': self._run_tts,
            }.get(self.workType)
            if handler is None:
                self.error.emit('Unknown work type', self.senderID, self.workType)
                return
            handler()
        except Exception as e:
            self.error.emit(str(e), self.senderID, self.workType)


    def _run_chat_api(self) -> None:
        objects = self.objects
        # LLM
        prompt = objects['prompt']
        if DEBUG_MODE:
            print(f'Start LLM work: {prompt}')
        # RAG
        ragRunnable = objects['ragRunnable']
        selectedText = objects['selectedText']
        ragContext = ''
        if ragRunnable is not None:
            retrieved = ragRunnable.retrieve(selectedText or prompt)
            if retrieved:
                if DEBUG_MODE:
                    print('RAG context:', '\n\n'.join(retrieved))
                ragContext = f"\n\nContext:\n---\n{ '\n\n'.join(retrieved) }\n---\n"
        # PDF extraction
        pdfFilePath = objects['pdfFilePath']
        pdfContext = ''
        if pdfFilePath:
            pdfContext = self.documentProcessor.extractTextFromPdf(pdfFilePath) + '\n\n'
        # Combine all
        prompt = f"{prompt}{ragContext}{pdfContext}{selectedText}"
        history = objects['messageHistory']
        # Agent usage
        agentTools = objects['agentTools']
        if agentTools and hasattr(objects['llmClient'], 'bind_tools'):
            content = self.runAgents(history, prompt)
        else: # No agent used
            runnable = objects['runnable']
            result = runnable.invoke(prompt, {'configurable': {'session_id': 'global'}})
            content = result.content if hasattr(result, 'content') else str(result)
        if DEBUG_MODE:
            print(f'End work: {self.senderID}\n  {content}')
        self.finished.emit(content, self.senderID, self.workType)


    def _run_transcribe_audio(self) -> None:
        """ Transcribe the audio into text """
        runnable = self.objects['runnable']
        blob     = Blob.from_path(self.objects['path'])
        docs     = runnable.parse(blob)
        content  = docs[0].page_content if docs else ''
        self.finished.emit(content, self.senderID, self.workType)


    def _run_ingest_rag(self) -> None:
        """ Ingest pdf files into the RAG database """
        runnable  = self.objects['runnable']
        filePaths = self.objects['filePaths']
        chunks    = runnable.ingestPaths(filePaths)
        self.finished.emit(f'Success | Chunks indexed: {chunks}', self.senderID, self.workType)


    def _run_tts(self) -> None:
        # TODO P4 TTS via Langchain, if available; ElevenLabs other good provider
        client   = OpenAI(api_key=self.objects['apiKey'])
        text     = self.objects['content']
        filePath = self.objects['filePaths']
        response = client.audio.speech.create(model='gpt-4o-mini-tts', voice='alloy', input=text)
        with open(filePath, 'wb') as f:
            f.write(response.read())


    def runAgents(self, history: Any, prompt: str) -> str:
        """ Run agents in loop of max 6 iterations.
        Args:
            history (Any): history of conversation so far
            prompt (str): current question
        Returns:
            str: answer to question
        """
        agentTools = self.objects['agentTools']
        toolMap = {t.name: t for t in agentTools}
        llmWithTools = self.objects['llmClient'].bind_tools(agentTools)
        # assemble messages
        messages: list[Any] = list(getattr(history, 'messages', []))
        userMessage = HumanMessage(content=prompt)
        messages.append(userMessage)
        newMessages: list[Any] = [userMessage]
        for _ in range(6):  # max. number of iterations
            aiMessage = llmWithTools.invoke(messages)  # run LLM call
            messages.append(aiMessage)
            newMessages.append(aiMessage)
            toolCalls = getattr(aiMessage, 'tool_calls', None) or []   # did the LLM decide to call a tool?
            if not toolCalls:
                if DEBUG_MODE:
                    print('No tools called')
                break
            for toolCall in toolCalls:
                name = toolCall['name']
                toolCallId = toolCall.get('id', '')
                if DEBUG_MODE:
                    print(f'Calling tool: {name}')
                if toolMap[name] is None:
                    toolResult = f"Tool '{name}' is not available."
                else:
                    try:
                        toolResult = toolMap[name].invoke(toolCall.get('args', {}))
                    except Exception as e:
                        toolResult = f"Tool '{name}' failed: {str(e)}"
                if DEBUG_MODE:
                    print(f'Tool result: {toolResult}')
                toolMessage = ToolMessage(content=str(toolResult), tool_call_id=toolCallId)
                messages.append(toolMessage)
                newMessages.append(toolMessage)
        # after all iterations, assemble reply
        if history and hasattr(history, 'add_message'): # changed as call-by-reference
            for msg in newMessages:
                try:
                    history.add_message(msg)
                except Exception:
                    pass
        content = messages[-1].content if hasattr(messages[-1], 'content') else str(messages[-1])
        return content
