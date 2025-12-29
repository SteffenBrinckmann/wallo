""" Custom QTextEdit with word wrap mode set to wrap at word boundary or anywhere. """
import re
from PySide6.QtCore import Qt, Signal, QMimeData  # pylint: disable=no-name-in-module
from PySide6.QtGui import (QTextOption, QKeyEvent, QAction, QKeySequence, QTextCursor, QTextDocumentFragment,  # pylint: disable=no-name-in-module
                           QContextMenuEvent, QMouseEvent)
from PySide6.QtWidgets import QApplication, QTextEdit, QMenu, QSizePolicy  # pylint: disable=no-name-in-module
from .editorSpellCheck import ENCHANT_AVAILABLE, SpellCheck
from .configFileManager import ConfigurationManager

class TextEdit(QTextEdit):
    """ Custom QTextEdit with word wrap mode set to wrap at word boundary or anywhere. """
    sendMessage = Signal(str)
    focused = Signal()

    def __init__(self, configManager:ConfigurationManager) -> None:
        """ Initialize the TextEdit with word wrap mode set to wrap at word boundary or anywhere
        Args:
            configManager (ConfigurationManager): configuration file manager that stores the dictionary
        """
        super().__init__()
        self.configManager = configManager
        self.setWordWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        self.ideazingMode = False
        self.spellCheckEnabled = ENCHANT_AVAILABLE
        self.highlighter  = SpellCheck(self.document(),
                                       self.configManager.get('dictionary')) if self.spellCheckEnabled else None
        self.reduceAction = QAction("Reduce block to highlighted text", self, shortcut=QKeySequence('Ctrl+R'))
        self.reduceAction.triggered.connect(self.reduce)
        self.deleteAction = QAction("Remove block", self, shortcut=QKeySequence('Ctrl+D'))
        self.deleteAction.triggered.connect(self.delete)
        # default: hide scrollbar and auto-fit when not editing
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.textChanged.connect(self._on_text_changed)
        # initial fit (resizeEvent will correct after layout)
        try:
            self.adjustHeightToContents()
        except Exception:
            pass


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


    def keyPressEvent(self, event:QKeyEvent) -> None:
        """ Handle key press events for ideazing mode message sending.
        Args:
            event (QKeyEvent): The key press event.
        """
        # For debugging: export current content to HTML file
        # if event.modifiers() == Qt.KeyboardModifier.ControlModifier and event.key()==Qt.Key.Key_Escape:
        #     with open('temp_debug.html', 'w', encoding='utf-8') as f:
        #         f.write(self.toHtml())
        if event.key() == Qt.Key.Key_C and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            cursor = self.textCursor()
            if cursor.hasSelection():
                # plainText = cursor.selectedText()
                fragment = QTextDocumentFragment(cursor)
                md = fragment.toMarkdown()
                QApplication.clipboard().setText(md)
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


    def reduce(self) -> None:
        """ Reduce the current block to the highlighted text. """
        html = self.delete()
        spans = TextEdit.spansWithBackground(html)
        htmlNew = '<ul>' + '\n'.join([f'<li>{i}</li>' for i in spans]) + '</ul><br>'
        self.insertHtml(htmlNew)


    def delete(self) -> str:
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
            self.highlighter = SpellCheck(self.document(), self.configManager.get('dictionary'))
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

    def focusInEvent(self, event):
        """When editor gains focus: allow scrolling and editing size expansion."""
        self.focused.emit()
        # allow the widget to expand vertically while editing and show scrollbar as needed
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setMaximumHeight(16777215)
        self.setMinimumHeight(0)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        super().focusInEvent(event)


    def focusOutEvent(self, event):
        """When losing focus: hide scrollbar and shrink to content height."""
        super().focusOutEvent(event)
        # hide scrollbar and shrink to content height so no extra empty lines appear
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.adjustHeightToContents()


    def adjustHeightToContents(self) -> None:
        """Compute document height and set the widget height to match content exactly.

        This hides the vertical scrollbar and avoids stray empty lines by using
        the document layout size and document margins.
        """
        doc = self.document()
        # ensure layout uses current viewport width for word-wrapping
        doc.setTextWidth(self.viewport().width())
        # documentLayout().documentSize() is reliable for the laid-out height
        try:
            docHeight = doc.documentLayout().documentSize().height()
        except Exception:
            docHeight = doc.size().height()
        # include document margins and frame width
        margin = doc.documentMargin()
        frame = getattr(self, 'frameWidth', lambda: 0)()
        newHeight = int(docHeight + 2*margin + 2*frame + 2)
        if newHeight < 1:
            newHeight = 1
        # lock height to prevent the parent layout from expanding the editor
        self.setFixedHeight(newHeight)


    def resizeEvent(self, event):
        """Recompute fitted height when width changes (only if unfocused)."""
        super().resizeEvent(event)
        # If not focused, adjust height to the new wrapping
        if not self.hasFocus():
            self.adjustHeightToContents()


    def _on_text_changed(self):
        # adjust only when not focused so typing doesn't constantly resize
        if not self.hasFocus():
            self.adjustHeightToContents()

    # connect textChanged to our handler
    # (connect after class definition is created)