"""
Document Tool Definitions.

Tools for PDF, OCR, and Document Generation.
"""

from typing import Any, Dict, List, Optional

from ag3ntwerk.tools.base import (
    BaseTool,
    ToolCategory,
    ToolMetadata,
    ToolParameter,
    ToolResult,
    ParameterType,
)


class ExtractPDFTextTool(BaseTool):
    """Extract text from PDF files."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="extract_pdf_text",
            description="Extract text content from a PDF file",
            category=ToolCategory.DOCUMENTS,
            tags=["pdf", "extract", "text", "document"],
            examples=[
                "Get text from the PDF",
                "Extract content from report.pdf",
                "Read the PDF document",
            ],
        )

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="file_path",
                description="Path to PDF file",
                param_type=ParameterType.STRING,
                required=True,
            ),
            ToolParameter(
                name="pages",
                description="Specific pages to extract (comma-separated)",
                param_type=ParameterType.STRING,
                required=False,
            ),
            ToolParameter(
                name="extract_tables",
                description="Also extract tables",
                param_type=ParameterType.BOOLEAN,
                required=False,
                default=False,
            ),
        ]

    async def _execute(self, **kwargs) -> ToolResult:
        file_path = kwargs.get("file_path")
        pages = kwargs.get("pages")
        extract_tables = kwargs.get("extract_tables", False)

        try:
            from ag3ntwerk.integrations.documents.pdf import PDFIntegration

            pdf = PDFIntegration()

            doc = await pdf.read(
                path=file_path,
                extract_text=True,
                extract_tables=extract_tables,
            )

            # Filter pages if specified
            page_content = []
            if pages:
                page_nums = [int(p.strip()) for p in pages.split(",")]
                for page in doc.pages:
                    if page.number in page_nums:
                        page_content.append(
                            {
                                "page": page.number,
                                "text": page.text,
                                "tables": page.tables if extract_tables else [],
                            }
                        )
            else:
                for page in doc.pages:
                    page_content.append(
                        {
                            "page": page.number,
                            "text": page.text,
                            "tables": page.tables if extract_tables else [],
                        }
                    )

            return ToolResult(
                success=True,
                data={
                    "title": doc.title,
                    "author": doc.author,
                    "num_pages": doc.num_pages,
                    "pages": page_content,
                    "full_text": "\n\n".join(p.text for p in doc.pages),
                },
            )

        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                error_type=type(e).__name__,
            )


class OCRImageTool(BaseTool):
    """Extract text from images using OCR."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="ocr_image",
            description="Extract text from an image using OCR",
            category=ToolCategory.DOCUMENTS,
            tags=["ocr", "image", "text", "scan"],
            examples=[
                "Read text from the image",
                "OCR this screenshot",
                "Extract text from scanned document",
            ],
        )

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="file_path",
                description="Path to image file",
                param_type=ParameterType.STRING,
                required=True,
            ),
            ToolParameter(
                name="language",
                description="Language code (e.g., 'eng', 'fra')",
                param_type=ParameterType.STRING,
                required=False,
                default="eng",
            ),
            ToolParameter(
                name="with_boxes",
                description="Include bounding boxes",
                param_type=ParameterType.BOOLEAN,
                required=False,
                default=False,
            ),
        ]

    async def _execute(self, **kwargs) -> ToolResult:
        file_path = kwargs.get("file_path")
        language = kwargs.get("language", "eng")
        with_boxes = kwargs.get("with_boxes", False)

        try:
            from ag3ntwerk.integrations.documents.ocr import OCRIntegration

            ocr = OCRIntegration()

            if with_boxes:
                result = await ocr.extract_with_boxes(
                    path=file_path,
                    language=language,
                )
                return ToolResult(
                    success=True,
                    data={
                        "text": result.text,
                        "confidence": result.confidence,
                        "boxes": [
                            {
                                "text": box.text,
                                "confidence": box.confidence,
                                "x": box.x,
                                "y": box.y,
                                "width": box.width,
                                "height": box.height,
                            }
                            for box in result.boxes
                        ],
                    },
                )
            else:
                result = await ocr.extract_text(
                    path=file_path,
                    language=language,
                )
                return ToolResult(
                    success=True,
                    data={
                        "text": result.text,
                        "confidence": result.confidence,
                    },
                )

        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                error_type=type(e).__name__,
            )


class GenerateDocumentTool(BaseTool):
    """Generate documents from templates."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="generate_document",
            description="Generate a document from a template",
            category=ToolCategory.DOCUMENTS,
            tags=["document", "generate", "template", "report"],
            examples=[
                "Generate a report document",
                "Create a document from template",
                "Generate the monthly report",
            ],
        )

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="template_name",
                description="Template name or path",
                param_type=ParameterType.STRING,
                required=True,
            ),
            ToolParameter(
                name="data",
                description="Data for template (JSON object)",
                param_type=ParameterType.DICT,
                required=True,
            ),
            ToolParameter(
                name="output_path",
                description="Output file path",
                param_type=ParameterType.STRING,
                required=True,
            ),
            ToolParameter(
                name="format",
                description="Output format (pdf, docx, md)",
                param_type=ParameterType.STRING,
                required=False,
                default="pdf",
            ),
        ]

    async def _execute(self, **kwargs) -> ToolResult:
        template_name = kwargs.get("template_name")
        data = kwargs.get("data", {})
        output_path = kwargs.get("output_path")
        output_format = kwargs.get("format", "pdf")

        try:
            from ag3ntwerk.integrations.documents.generator import (
                DocumentGenerator,
                DocumentFormat,
            )

            generator = DocumentGenerator()

            # Map format string to enum
            format_map = {
                "pdf": DocumentFormat.PDF,
                "docx": DocumentFormat.DOCX,
                "md": DocumentFormat.MARKDOWN,
                "markdown": DocumentFormat.MARKDOWN,
                "html": DocumentFormat.HTML,
            }
            doc_format = format_map.get(output_format.lower(), DocumentFormat.PDF)

            result_path = await generator.generate(
                template=template_name,
                data=data,
                output_path=output_path,
                format=doc_format,
            )

            return ToolResult(
                success=True,
                data={
                    "output_path": result_path,
                    "format": output_format,
                },
            )

        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                error_type=type(e).__name__,
            )
