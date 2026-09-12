"""Versioned WALLO document and recovery file handling."""
import json
from pathlib import Path
from typing import Callable, TypedDict
from PySide6.QtWidgets import QFileDialog, QMessageBox, QWidget  # pylint: disable=no-name-in-module

APPLICATION = 'WALLO'
FORMAT_VERSION = 1


class ExchangeData(TypedDict):
    """Persisted text for one exchange/turn."""
    text1: str
    text2: str


class SelectionData(TypedDict):
    """Persisted toolbar selection names."""
    profile: str
    service: str
    model: str


class DocumentData(TypedDict):
    """Versioned WALLO document data."""
    application: str
    formatVersion: int
    selection: SelectionData
    exchanges: list[ExchangeData]


class WalloFiles:
    """Read, write, and validate WALLO documents and recovery data."""

    def __init__(self, recoveryPath: Path) -> None:
        """Initialize file handling for one WALLO instance.

        Args:
            recoveryPath: Location used for crash recovery.
        """
        self.recoveryPath = recoveryPath


    def documentData(self, exchanges: list[ExchangeData], selection: SelectionData) -> DocumentData:
        """Build one versioned document payload.

        Args:
            exchanges: Persisted exchange text in document order.
            selection: Current profile, service, and model names.
        Returns:
            Valid document payload for manual save or recovery.
        """
        return {'application': APPLICATION, 'formatVersion': FORMAT_VERSION,
                'selection': selection, 'exchanges': exchanges}


    def loadRecovery(self) -> DocumentData | None:
        """Load valid recovery data without showing user-facing errors.

        Returns:
            Recovery document, or None when unavailable or invalid.
        """
        try:
            return self._read(self.recoveryPath)
        except ValueError:
            return None


    def saveRecovery(self, document: DocumentData) -> None:
        """Atomically write recovery data and ignore filesystem failures.

        Args:
            document: Current versioned WALLO document.
        """
        try:
            self._write(self.recoveryPath, document)
        except ValueError:
            pass


    def removeRecovery(self) -> None:
        """Remove recovery data after a normal application shutdown."""
        try:
            self.recoveryPath.unlink()
        except OSError:
            pass


    def openDocument(self, parent: QWidget, loadCb: Callable[[DocumentData], None]) -> None:
        """Show an Open dialog and read a versioned WALLO document.

        Args:
            parent: Widget that owns dialogs and error messages.
            loadCb: Callback that applies a successfully loaded document.
        """
        fileName, _ = QFileDialog.getOpenFileName(parent, 'Open WALLO Document', str(Path.home()),
                                                   'WALLO documents (*.json)')
        if not fileName:
            return
        try:
            loadCb(self._read(Path(fileName)))
        except ValueError as error:
            QMessageBox.critical(parent, 'Open Document Error', str(error))


    def saveDocument(self, parent: QWidget, document: DocumentData) -> None:
        """Show Save As and write a versioned WALLO document.

        Args:
            parent: Widget that owns dialogs and error messages.
            document: Current versioned WALLO document.
        """
        fileName, _ = QFileDialog.getSaveFileName(parent, 'Save WALLO Document', str(Path.home()),
                                                   'WALLO documents (*.json)')
        if not fileName:
            return
        path = Path(fileName)
        if not path.suffix:
            path = path.with_suffix('.json')
        try:
            self._write(path, document)
        except ValueError as error:
            QMessageBox.critical(parent, 'Save Document Error', str(error))


    def _read(self, path: Path) -> DocumentData:
        """Read and validate one WALLO JSON document.

        Args:
            path: File to read.
        Returns:
            Validated WALLO document.
        Raises:
            ValueError: If reading, decoding, or validation fails.
        """
        try:
            with open(path, encoding='utf-8') as fileHandle:
                data = json.load(fileHandle)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError(f'Cannot read WALLO document: {error}') from error
        return self._validate(data)


    def _write(self, path: Path, document: DocumentData) -> None:
        """Atomically write a validated WALLO JSON document.

        Args:
            path: Final file location.
            document: Versioned document to write.
        Raises:
            ValueError: If validation or writing fails.
        """
        validated = self._validate(document)
        tempPath = path.with_name(path.name + '.tmp')
        try:
            with open(tempPath, 'w', encoding='utf-8') as fileHandle:
                json.dump(validated, fileHandle, indent=2)
            tempPath.replace(path)
        except OSError as error:
            raise ValueError(f'Cannot save WALLO document: {error}') from error


    @staticmethod
    def _validate(data: object) -> DocumentData:
        """Validate the complete version 1 WALLO document schema.

        Args:
            data: Decoded JSON value to validate.
        Returns:
            Validated document with typed values.
        Raises:
            ValueError: If data differs from the required format.
        """
        if not isinstance(data, dict) or data.get('application') != APPLICATION or \
                data.get('formatVersion') != FORMAT_VERSION:
            raise ValueError('Not a supported WALLO document')
        selection = data.get('selection')
        exchanges = data.get('exchanges')
        if not isinstance(selection, dict) or not isinstance(exchanges, list):
            raise ValueError('WALLO document has invalid selections or exchanges')
        if any(not isinstance(selection.get(name), str) for name in ('profile', 'service', 'model')):
            raise ValueError('WALLO document has invalid selection names')
        result: list[ExchangeData] = []
        for exchange in exchanges:
            if not isinstance(exchange, dict) or not isinstance(exchange.get('text1'), str) or \
                    not isinstance(exchange.get('text2'), str):
                raise ValueError('WALLO document has invalid exchange text')
            result.append({'text1': exchange['text1'], 'text2': exchange['text2']})
        return {'application': APPLICATION, 'formatVersion': FORMAT_VERSION,
                'selection': {'profile': selection['profile'], 'service': selection['service'],
                              'model': selection['model']}, 'exchanges': result}
