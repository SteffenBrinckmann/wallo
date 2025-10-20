from typing import Optional
from PySide6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor
try:
    import enchant
    from enchant.tokenize import get_tokenizer
    ENCHANT_AVAILABLE = True
except ImportError:
    ENCHANT_AVAILABLE = False


class SpellCheck(QSyntaxHighlighter):
    """Syntax highlighter that marks misspelled words with red wavy underlines."""
    def __init__(self, parent, dictionary:Optional[str]='en_US') -> None:
        """Initialize the spell checker highlighter.
        Args:
            parent: The parent QTextDocument.
            dictionary (str): The dictionary language code (e.g., 'en_US', 'de_DE').
        """
        super().__init__(parent)
        self.spellDict = None
        self.tokenizer = None
        if ENCHANT_AVAILABLE and dictionary:
            try:
                self.spellDict = enchant.Dict(dictionary)
                self.tokenizer = get_tokenizer(dictionary)
            except enchant.errors.DictNotFoundError:
                print(f"Dictionary '{dictionary}' not found. Spell checking disabled.")
        self.misspelledFormat = QTextCharFormat()
        self.misspelledFormat.setUnderlineColor(QColor("red"))
        self.misspelledFormat.setUnderlineStyle(QTextCharFormat.UnderlineStyle.WaveUnderline)
        # Add a subtle background to make misspellings more visible
        self.misspelledFormat.setBackground(QColor(255, 200, 200, 30))  # Very light red with transparency


    def highlightBlock(self, text:str) -> None:
        """Highlight misspelled words in the given text block.
        Args:
            text (str): The text block to check for spelling.
        """
        if not self.spellDict or not self.tokenizer:
            return
        for word, pos in self.tokenizer(text):
            if not self.spellDict.check(word):
                self.setFormat(pos, len(word), self.misspelledFormat)

