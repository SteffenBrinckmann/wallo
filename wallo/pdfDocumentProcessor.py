"""PDF processing utilities for the Wallo application."""
from pathlib import Path
import pdfplumber


class PdfDocumentProcessor:
    """Handles PDF processing and text extraction."""

    def __init__(self) -> None:
        """Initialize the document processor."""

    def extractTextFromPdf(self, pdfPath: str) -> str:
        """Extract text content from a PDF file.

        Args:
            pdfPath: Path to the PDF file.

        Returns:
            Extracted text content.

        Raises:
            ValueError: If PDF cannot be processed or contains no text.
            FileNotFoundError: If PDF file doesn't exist.
        """
        pdfFile = Path(pdfPath)
        if not pdfFile.is_file():
            raise ValueError(f"Path is not a file: {pdfPath}")
        try:
            with pdfplumber.open(pdfPath) as pdf:
                content = "\\n".join(page.extract_text() or "" for page in pdf.pages)
        except Exception as e:
            raise ValueError(f"Error processing PDF file: {e}") from e
        if not content.strip():
            raise ValueError("PDF Error: No text found in the PDF.")
        return content


    def validatePdfFile(self, pdfPath: str) -> bool:
        """Validate if a file is a valid PDF.

        Args:
            pdfPath: Path to the PDF file.

        Returns:
            True if the file is a valid PDF, False otherwise.
        """
        try:
            pdfFile = Path(pdfPath)
            if not pdfFile.exists() or not pdfFile.is_file():
                return False
            # Try to open the PDF to validate it
            with pdfplumber.open(pdfPath) as pdf:
                # Check if we can access at least one page
                if len(pdf.pages) == 0:
                    return False
                # Try to access the first page
                _ = pdf.pages[0]
            return True
        except Exception:
            return False


    def extractTextFromPage(self, pdfPath: str, pageNum: int) -> str:
        """Extract text from a specific page of a PDF.

        Args:
            pdfPath: Path to the PDF file.
            pageNum: Page number (0-based).

        Returns:
            Extracted text from the specified page.

        Raises:
            ValueError: If PDF cannot be processed or page doesn't exist.
            FileNotFoundError: If PDF file doesn't exist.
        """
        if not self.validatePdfFile(pdfPath):
            raise ValueError(f"Invalid PDF file: {pdfPath}")
        try:
            with pdfplumber.open(pdfPath) as pdf:
                if pageNum >= len(pdf.pages) or pageNum < 0:
                    raise ValueError(f"Page {pageNum} does not exist in PDF")
                page = pdf.pages[pageNum]
                content = page.extract_text()
                return content or ""
        except Exception as e:
            raise ValueError(f"Error extracting text from page {pageNum}: {e}") from e
