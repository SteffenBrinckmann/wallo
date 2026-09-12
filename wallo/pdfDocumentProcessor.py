"""PDF text extraction utility for WALLO."""
from pathlib import Path
import pdfplumber

def extractTextFromPdf(pdfPath: str) -> str:
    """Extract text content from a PDF file.

        Args:
            pdfPath: Path to the PDF file.

        Returns:
            Extracted text content.

    Raises:
        ValueError: If the file cannot be processed or contains no text.
    """
    pdfFile = Path(pdfPath)
    if not pdfFile.is_file():
        raise ValueError(f'Path is not a file: {pdfPath}')
    try:
        with pdfplumber.open(pdfPath) as pdf:
            content = '\\n'.join(page.extract_text() or '' for page in pdf.pages)
    except Exception as error:
        raise ValueError(f'Error processing PDF file: {error}') from error
    if not content.strip():
        raise ValueError('PDF Error: No text found in the PDF.')
    return content
