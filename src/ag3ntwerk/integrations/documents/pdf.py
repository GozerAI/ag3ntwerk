"""
PDF Integration for ag3ntwerk.

Provides PDF processing and generation.

Requirements:
    - pip install pypdf reportlab pdfplumber

PDF is ideal for:
    - Report generation
    - Document parsing
    - Form filling
    - Invoice creation
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
import io

logger = logging.getLogger(__name__)


@dataclass
class PDFPage:
    """Represents a PDF page."""

    number: int
    text: str = ""
    width: float = 0
    height: float = 0
    tables: List[List[List[str]]] = field(default_factory=list)


@dataclass
class PDFDocument:
    """Represents a PDF document."""

    path: str
    pages: List[PDFPage] = field(default_factory=list)
    title: str = ""
    author: str = ""
    subject: str = ""
    creator: str = ""
    creation_date: Optional[datetime] = None
    modification_date: Optional[datetime] = None
    num_pages: int = 0


class PDFIntegration:
    """
    Integration for PDF processing.

    Example:
        pdf = PDFIntegration()

        # Read PDF
        doc = await pdf.read("document.pdf")
        print(doc.pages[0].text)

        # Extract tables
        tables = await pdf.extract_tables("report.pdf")

        # Create PDF
        await pdf.create_report(
            "output.pdf",
            title="Monthly Report",
            content={"sales": 10000, "users": 500},
        )
    """

    def __init__(self):
        """Initialize PDF integration."""
        pass

    async def read(
        self,
        path: str,
        extract_text: bool = True,
        extract_tables: bool = False,
    ) -> PDFDocument:
        """
        Read a PDF document.

        Args:
            path: PDF file path
            extract_text: Extract text content
            extract_tables: Extract tables

        Returns:
            PDFDocument
        """
        loop = asyncio.get_running_loop()

        def _read():
            try:
                import pdfplumber
            except ImportError:
                raise ImportError("pdfplumber not installed. Install with: pip install pdfplumber")

            pages = []
            metadata = {}

            with pdfplumber.open(path) as pdf:
                metadata = pdf.metadata or {}

                for i, page in enumerate(pdf.pages):
                    page_data = PDFPage(
                        number=i + 1,
                        width=page.width,
                        height=page.height,
                    )

                    if extract_text:
                        page_data.text = page.extract_text() or ""

                    if extract_tables:
                        tables = page.extract_tables() or []
                        page_data.tables = tables

                    pages.append(page_data)

            return PDFDocument(
                path=path,
                pages=pages,
                title=metadata.get("Title", ""),
                author=metadata.get("Author", ""),
                subject=metadata.get("Subject", ""),
                creator=metadata.get("Creator", ""),
                num_pages=len(pages),
            )

        return await loop.run_in_executor(None, _read)

    async def extract_text(self, path: str) -> str:
        """Extract all text from PDF."""
        doc = await self.read(path, extract_text=True)
        return "\n\n".join(page.text for page in doc.pages)

    async def extract_tables(self, path: str) -> List[List[List[str]]]:
        """Extract all tables from PDF."""
        doc = await self.read(path, extract_tables=True)
        tables = []
        for page in doc.pages:
            tables.extend(page.tables)
        return tables

    async def merge(
        self,
        input_paths: List[str],
        output_path: str,
    ) -> str:
        """
        Merge multiple PDFs into one.

        Args:
            input_paths: List of PDF paths
            output_path: Output file path

        Returns:
            Output file path
        """
        loop = asyncio.get_running_loop()

        def _merge():
            try:
                from pypdf import PdfWriter, PdfReader
            except ImportError:
                raise ImportError("pypdf not installed. Install with: pip install pypdf")

            writer = PdfWriter()

            for path in input_paths:
                reader = PdfReader(path)
                for page in reader.pages:
                    writer.add_page(page)

            with open(output_path, "wb") as f:
                writer.write(f)

            return output_path

        return await loop.run_in_executor(None, _merge)

    async def split(
        self,
        path: str,
        output_dir: str,
        pages: Optional[List[int]] = None,
    ) -> List[str]:
        """
        Split PDF into individual pages.

        Args:
            path: Input PDF path
            output_dir: Output directory
            pages: Specific pages to extract (all if None)

        Returns:
            List of output file paths
        """
        loop = asyncio.get_running_loop()

        def _split():
            try:
                from pypdf import PdfWriter, PdfReader
            except ImportError:
                raise ImportError("pypdf not installed. Install with: pip install pypdf")

            output_paths = []
            reader = PdfReader(path)
            base_name = Path(path).stem

            page_nums = pages or range(len(reader.pages))

            for i in page_nums:
                writer = PdfWriter()
                writer.add_page(reader.pages[i])

                output_path = f"{output_dir}/{base_name}_page_{i + 1}.pdf"
                with open(output_path, "wb") as f:
                    writer.write(f)
                output_paths.append(output_path)

            return output_paths

        return await loop.run_in_executor(None, _split)

    async def create_report(
        self,
        output_path: str,
        title: str,
        content: Dict[str, Any],
        template: str = "simple",
    ) -> str:
        """
        Create a PDF report.

        Args:
            output_path: Output file path
            title: Report title
            content: Report content dict
            template: Template style

        Returns:
            Output file path
        """
        loop = asyncio.get_running_loop()

        def _create():
            try:
                from reportlab.lib.pagesizes import letter
                from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
                from reportlab.platypus import (
                    SimpleDocTemplate,
                    Paragraph,
                    Spacer,
                    Table,
                    TableStyle,
                )
                from reportlab.lib import colors
            except ImportError:
                raise ImportError("reportlab not installed. Install with: pip install reportlab")

            doc = SimpleDocTemplate(output_path, pagesize=letter)
            styles = getSampleStyleSheet()
            story = []

            # Title
            title_style = ParagraphStyle(
                "Title",
                parent=styles["Heading1"],
                fontSize=24,
                spaceAfter=30,
            )
            story.append(Paragraph(title, title_style))
            story.append(Spacer(1, 20))

            # Content
            for key, value in content.items():
                if isinstance(value, (list, tuple)):
                    # Table
                    if value and isinstance(value[0], (list, tuple)):
                        table = Table(value)
                        table.setStyle(
                            TableStyle(
                                [
                                    ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                                ]
                            )
                        )
                        story.append(Paragraph(key.title(), styles["Heading2"]))
                        story.append(Spacer(1, 10))
                        story.append(table)
                        story.append(Spacer(1, 20))
                    else:
                        story.append(Paragraph(key.title(), styles["Heading2"]))
                        for item in value:
                            story.append(Paragraph(f"• {item}", styles["Normal"]))
                        story.append(Spacer(1, 10))
                elif isinstance(value, dict):
                    story.append(Paragraph(key.title(), styles["Heading2"]))
                    for k, v in value.items():
                        story.append(Paragraph(f"{k}: {v}", styles["Normal"]))
                    story.append(Spacer(1, 10))
                else:
                    story.append(Paragraph(f"<b>{key.title()}:</b> {value}", styles["Normal"]))
                    story.append(Spacer(1, 5))

            doc.build(story)
            return output_path

        return await loop.run_in_executor(None, _create)

    async def add_watermark(
        self,
        input_path: str,
        output_path: str,
        watermark_text: str,
        opacity: float = 0.3,
    ) -> str:
        """
        Add watermark to PDF.

        Args:
            input_path: Input PDF path
            output_path: Output PDF path
            watermark_text: Watermark text
            opacity: Watermark opacity

        Returns:
            Output file path
        """
        loop = asyncio.get_running_loop()

        def _watermark():
            try:
                from pypdf import PdfWriter, PdfReader
                from reportlab.lib.pagesizes import letter
                from reportlab.pdfgen import canvas
                from reportlab.lib import colors
            except ImportError:
                raise ImportError("pypdf and reportlab not installed")

            # Create watermark
            packet = io.BytesIO()
            c = canvas.Canvas(packet, pagesize=letter)
            c.setFillColor(colors.gray, alpha=opacity)
            c.setFont("Helvetica", 50)
            c.saveState()
            c.translate(300, 400)
            c.rotate(45)
            c.drawCentredString(0, 0, watermark_text)
            c.restoreState()
            c.save()
            packet.seek(0)

            watermark_pdf = PdfReader(packet)
            watermark_page = watermark_pdf.pages[0]

            reader = PdfReader(input_path)
            writer = PdfWriter()

            for page in reader.pages:
                page.merge_page(watermark_page)
                writer.add_page(page)

            with open(output_path, "wb") as f:
                writer.write(f)

            return output_path

        return await loop.run_in_executor(None, _watermark)

    async def encrypt(
        self,
        input_path: str,
        output_path: str,
        password: str,
    ) -> str:
        """Encrypt a PDF with password."""
        loop = asyncio.get_running_loop()

        def _encrypt():
            try:
                from pypdf import PdfWriter, PdfReader
            except ImportError:
                raise ImportError("pypdf not installed")

            reader = PdfReader(input_path)
            writer = PdfWriter()

            for page in reader.pages:
                writer.add_page(page)

            writer.encrypt(password)

            with open(output_path, "wb") as f:
                writer.write(f)

            return output_path

        return await loop.run_in_executor(None, _encrypt)

    async def get_metadata(self, path: str) -> Dict[str, Any]:
        """Get PDF metadata."""
        doc = await self.read(path, extract_text=False)
        return {
            "title": doc.title,
            "author": doc.author,
            "subject": doc.subject,
            "creator": doc.creator,
            "num_pages": doc.num_pages,
        }
