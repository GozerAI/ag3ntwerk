"""
Document Processing Integrations for ag3ntwerk.

This package provides integrations for document operations:
- PDF: Processing and generation
- OCR: Text extraction from images
- Documents: Document generation (Docx, Markdown)
"""

from ag3ntwerk.integrations.documents.pdf import (
    PDFIntegration,
    PDFDocument,
    PDFPage,
)
from ag3ntwerk.integrations.documents.ocr import (
    OCRIntegration,
    OCRConfig,
    OCRResult,
)
from ag3ntwerk.integrations.documents.generator import (
    DocumentGenerator,
    DocumentTemplate,
    DocumentFormat,
)

__all__ = [
    "PDFIntegration",
    "PDFDocument",
    "PDFPage",
    "OCRIntegration",
    "OCRConfig",
    "OCRResult",
    "DocumentGenerator",
    "DocumentTemplate",
    "DocumentFormat",
]
