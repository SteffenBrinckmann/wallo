"""RAG document ingestion and indexing logic for Wallo.

Keeps things explicit and local:
- Loads local files / folders
- Chunks text
- Embeds and stores in a persistent vector store
"""
import os
import traceback
from typing import Iterable, List
from langchain_community.document_loaders import TextLoader, PyPDFLoader, Docx2txtLoader
from langchain_community.vectorstores import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from .configFileManager import ConfigurationManager

RAG_DB_PATH = os.path.expanduser('~/.wallo_rag')
CHUNK_SIZE = 800
CHUNK_OVERLAP = 100


class RagIndexer:
    """Handles ingestion and retrieval of local files into a RAG vector store."""

    def __init__(self, configManager: ConfigurationManager) -> None:
        self.embeddings = OpenAIEmbeddings(api_key=configManager.getServiceByName('openAI')['api'])  #TODO make sure this exists and always openAI
        self.textSplitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
        self.vectorStore = Chroma(persist_directory=RAG_DB_PATH, embedding_function=self.embeddings)


    def ingestPaths(self, paths: Iterable[str]) -> int:
        """Ingest files or directories into the vector store.

        Args:
            paths: Files or directories to ingest

        Returns:
            Number of chunks indexed
        """
        documents = []
        for path in paths:
            if os.path.isdir(path):
                documents.extend(self._loadDirectory(path))
            elif os.path.isfile(path):
                documents.extend(self._loadFile(path))
        if not documents:
            return 0
        chunks = self.textSplitter.split_documents(documents)
        self.vectorStore.add_documents(chunks)
        self.vectorStore.persist()
        return len(chunks)


    def retrieve(self, query: str, k: int = 4) -> list[str]:
        """Retrieve most relevant text chunks for a query.
        Args:
          query (str): text to search in database
          k (int): number of chunks to return (default: 4
        Returns:
          List of most relevant text chunks
        """
        try:
            docs = self.vectorStore.similarity_search(query, k=k)
            return [doc.page_content for doc in docs]
        except Exception:
            return []


    def _loadDirectory(self, directory: str) -> List:
        """ Load all files in a directory into the vector store
        Args:
          directory (str): directory path
        Returns:
          List of documents
        """
        docs = []
        for root, _, files in os.walk(directory):
            for name in files:
                docs.extend(self._loadFile(os.path.join(root, name)))
        return docs


    def _loadFile(self, filePath: str) -> List:
        """ Load a single file into the vector store
        Args:
          filePath (str): file path
        Returns:
          List of documents
        """
        ext = os.path.splitext(filePath)[1].lower()
        try:
            if ext in {'.txt', '.md'}:
                return TextLoader(filePath, encoding='utf-8').load()
            if ext == '.pdf':
                return PyPDFLoader(filePath).load()
            if ext == '.docx':
                return Docx2txtLoader(filePath).load()
        except Exception:
            traceback.print_exc()
            return []
        return []
