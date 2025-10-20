""" Custom QTextEdit with word wrap mode set to wrap at word boundary or anywhere. """
import re
from PySide6.QtCore import Qt, Signal, QMimeData  # pylint: disable=no-name-in-module
from PySide6.QtGui import (QTextOption, QKeyEvent, QAction, QKeySequence, QTextCursor, QTextDocumentFragment,  # pylint: disable=no-name-in-module
                           QContextMenuEvent, QMouseEvent)
from PySide6.QtWidgets import QApplication, QTextEdit, QMenu  # pylint: disable=no-name-in-module
from .editorSpellCheck import ENCHANT_AVAILABLE, SpellCheck
from .configFileManager import ConfigurationManager

class TextEdit(QTextEdit):
    """ Custom QTextEdit with word wrap mode set to wrap at word boundary or anywhere. """
    sendMessage = Signal(str)
    def __init__(self, configManager:ConfigurationManager) -> None:
        """ Initialize the TextEdit with word wrap mode set to wrap at word boundary or anywhere
        Args:
            configManager (ConfigurationManager): configuration file manager that stores the dictionary
        """
        super().__init__()
        self.setWordWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        self.ideazingMode = False
        self.spellCheckEnabled = ENCHANT_AVAILABLE
        self.highlighter  = SpellCheck(self.document(),
                                       configManager.get('dictionary')) if self.spellCheckEnabled else None
        self.reduceAction = QAction("Reduce block to highlighted text", self, shortcut=QKeySequence('Ctrl+R'))
        self.reduceAction.triggered.connect(self._reduce)
        self.deleteAction = QAction("Remove block", self, shortcut=QKeySequence('Ctrl+D'))
        self.deleteAction.triggered.connect(self._delete)


    def contextMenuEvent(self, event:QContextMenuEvent) -> None:
        """Create a context menu based on the standard menu, plus custom actions and spelling suggestions."""
        menu: QMenu = self.createStandardContextMenu()
        if self.spellCheckEnabled and self.highlighter and self.highlighter.spellDict:
            cursor = self.cursorForPosition(event.pos())
            cursor.select(QTextCursor.SelectionType.WordUnderCursor)
            word = cursor.selectedText()
            if word and not self.highlighter.spellDict.check(word):
                suggestions = self.highlighter.spellDict.suggest(word)[:10]
                if suggestions:
                    menu.insertSeparator(menu.actions()[0])
                    for suggestion in suggestions:
                        action = menu.addAction(suggestion)
                        action.triggered.connect(lambda checked=False, s=suggestion, c=cursor: self._replaceWord(c, s))
                        menu.insertAction(menu.actions()[0], action)
                    addToDictAction = QAction("Add to dictionary", self)
                    addToDictAction.triggered.connect(lambda: self._addToDictionary(word))
                    menu.insertAction(menu.actions()[0], addToDictAction)
                    menu.insertSeparator(menu.actions()[0])
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


    def setSpellCheckEnabled(self, enabled:bool) -> None:
        """ Enable or disable spell checking.
        Args:
            enabled (bool): True to enable spell checking, False to disable.
        """
        self.spellCheckEnabled = enabled and ENCHANT_AVAILABLE
        if self.spellCheckEnabled and not self.highlighter:
            configManager = ConfigurationManager()
            self.highlighter = SpellCheck(self.document(), configManager.get('dictionary'))
        if self.highlighter:
            if self.spellCheckEnabled:
                self.highlighter.rehighlight()
            else:
                # Clear highlighting by disabling the highlighter
                self.highlighter.setDocument(None)


    def _replaceWord(self, cursor:QTextCursor, newWord:str) -> None:
        """Replace the word at the cursor position with the given word.
        Args:
            cursor (QTextCursor): The cursor selecting the word to replace.
            newWord (str): The replacement word.
        """
        cursor.beginEditBlock()
        cursor.removeSelectedText()
        cursor.insertText(newWord)
        cursor.endEditBlock()


    def _addToDictionary(self, word:str) -> None:
        """Add a word to the personal dictionary.
        Args:
            word (str): The word to add to the dictionary.
        """
        if self.highlighter and self.highlighter.spellDict:
            self.highlighter.spellDict.add(word)
            self.highlighter.rehighlight()
