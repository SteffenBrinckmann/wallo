""" Custom QTextEdit with word wrap mode set to wrap at word boundary or anywhere. """
import re
from PySide6.QtCore import Qt, Signal, QMimeData  # pylint: disable=no-name-in-module
from PySide6.QtGui import (QTextOption, QKeyEvent, QAction, QKeySequence, QTextCursor, QTextDocumentFragment,  # pylint: disable=no-name-in-module
                           QContextMenuEvent, QMouseEvent)
from PySide6.QtWidgets import QApplication, QTextEdit, QMenu  # pylint: disable=no-name-in-module


class TextEdit(QTextEdit):
    """ Custom QTextEdit with word wrap mode set to wrap at word boundary or anywhere. """
    sendMessage = Signal(str)
    def __init__(self) -> None:
        """ Initialize the TextEdit with word wrap mode set to wrap at word boundary or anywhere """
        super().__init__()
        self.setWordWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        self.ideazingMode = False
        self.reduceAction = QAction("Reduce block to highlighted text", self, shortcut=QKeySequence('Ctrl+R'))
        self.reduceAction.triggered.connect(self._reduce)
        self.deleteAction = QAction("Remove block", self, shortcut=QKeySequence('Ctrl+D'))
        self.deleteAction.triggered.connect(self._delete)


    def contextMenuEvent(self, event:QContextMenuEvent) -> None:
        """Create a context menu based on the standard menu, plus custom actions."""
        menu: QMenu = self.createStandardContextMenu()
        menu.addSeparator()
        menu.addAction(self.reduceAction)
        menu.addAction(self.deleteAction)
        menu.exec(event.globalPos())


    # EVENTS
    def insertFromMimeData(self, source:QMimeData) -> None:
        """Override paste behavior to remove hard line breaks from pasted text.
        Args:
            source (QMimeData): The mime data being pasted.
        """
        if source.hasText():
            text = source.text()
            # Replace single newlines with spaces, but preserve double newlines (paragraph breaks)
            text = re.sub(r'(?<!\n)\n(?!\n)', ' ', text)
            self.insertPlainText(text)
        else:
            super().insertFromMimeData(source)


    def copy(self) -> None:
        """ Copy the selected text to the clipboard """
        cursor = self.textCursor()
        if cursor.hasSelection():
            text = cursor.selectedText()
            print(text)
            QApplication.clipboard().setText(text)
        else:
            super().copy()


    def keyPressEvent(self, event:QKeyEvent) -> None:
        """ Handle key press events for ideazing mode message sending.
        Args:
            event (QKeyEvent): The key press event.
        """
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier and event.key()==Qt.Key.Key_Escape:
            with open('temp_debug.html', 'w', encoding='utf-8') as f:
                f.write(self.toHtml())
        elif self.ideazingMode and event.key() == Qt.Key.Key_Return and \
                                   event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            text = self.toPlainText().strip()
            if text:
                self.sendMessage.emit(text)
            event.accept()
        else:
            super().keyPressEvent(event)


    def mouseReleaseEvent(self, e:QMouseEvent) -> None:
        """ Handle mouse release events.
        Args:
            e: The mouse release event.
        """
        if self.ideazingMode and e.modifiers()==Qt.KeyboardModifier.ControlModifier and \
                                 self.textCursor().hasSelection():
            cursor = self.textCursor()
            selectedText = cursor.selectedText()
            cursor.removeSelectedText()
            cursor.clearSelection()
            styledContent = f'<span style="background-color: #777700;">{selectedText}</span>'
            cursor.insertHtml(styledContent)
            e.accept()
        return super().mouseReleaseEvent(e)


    def _reduce(self) -> None:
        """ Reduce the current block to the highlighted text. """
        html = self._delete()
        spans = TextEdit.spansWithBackground(html)
        htmlNew = '<ul>' + '\n'.join([f'<li>{i}</li>' for i in spans]) + '</ul><br>'
        self.insertHtml(htmlNew)


    def _delete(self) -> str:
        """ Remove the current block. """
        #Choose entire block
        cursor = self.textCursor()
        block = cursor.block()
        start = block.position()
        docLen = max(0, self.document().characterCount() - 1)
        end = min(start+block.length(), docLen)  # no -1, include block separator
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
        self.setTextCursor(cursor)
        self.setFocus()
        fragment = QTextDocumentFragment(cursor)
        #Delete
        cursor.removeSelectedText()
        return fragment.toHtml()


    @staticmethod
    def spansWithBackground(html: str) -> list[str]:
        """Return list of (plain text) for <span> tags with inline background.
        Matches inline style attributes containing
        'background' or 'background-color' and extracts the color/value.

        Args:
            html (str): The HTML content to search.
        Returns:
            list[str]: List of plain text contained within matching <span> tags.
        """
        span      = re.compile(r'<span\b([^>]*)>(.*?)</span>', re.IGNORECASE | re.DOTALL)
        styleAttr = re.compile(r'style\s*=\s*([\'"])(.*?)\1', re.IGNORECASE | re.DOTALL)
        results: list[str] = []
        for m in span.finditer(html):
            attrs = m.group(1)
            innerHtml = m.group(2)
            styleMatch = styleAttr.search(attrs)
            if not styleMatch:
                continue
            style = styleMatch.group(2)
            if 'background' not in style.lower():
                continue
            text = re.sub(r'<[^>]+>', '', innerHtml) # strip any inner HTML tags to get plain text
            results.append(text)
        return results


    def setIdeazingMode(self, enabled:bool) -> None:
        """ Enable or disable ideazing mode.
        Args:
            enabled (bool): True to enable ideazing mode, False to disable.
        """
        self.ideazingMode = enabled
