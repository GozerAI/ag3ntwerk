"""
OCR Integration for ag3ntwerk.

Provides text extraction from images using Tesseract.

Requirements:
    - pip install pytesseract pillow
    - Install Tesseract: https://github.com/tesseract-ocr/tesseract

OCR is ideal for:
    - Document digitization
    - Invoice processing
    - Receipt scanning
    - Form data extraction
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class OCRConfig:
    """Configuration for OCR."""

    tesseract_cmd: str = ""  # Path to tesseract executable
    language: str = "eng"  # Language code
    psm: int = 3  # Page segmentation mode
    oem: int = 3  # OCR engine mode
    dpi: int = 300  # DPI for image processing


@dataclass
class OCRBox:
    """Represents a detected text box."""

    text: str
    confidence: float
    x: int
    y: int
    width: int
    height: int
    level: int = 0  # 1=page, 2=block, 3=paragraph, 4=line, 5=word


@dataclass
class OCRResult:
    """Result of OCR processing."""

    text: str
    boxes: List[OCRBox] = field(default_factory=list)
    confidence: float = 0.0
    language: str = ""
    source_path: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class OCRIntegration:
    """
    Integration for OCR text extraction.

    Example:
        ocr = OCRIntegration()

        # Extract text from image
        result = await ocr.extract_text("document.png")
        print(result.text)

        # Get text with bounding boxes
        result = await ocr.extract_with_boxes("form.jpg")
        for box in result.boxes:
            print(f"{box.text} at ({box.x}, {box.y})")

        # Process multiple images
        results = await ocr.batch_extract(["page1.png", "page2.png"])
    """

    def __init__(self, config: Optional[OCRConfig] = None):
        """Initialize OCR integration."""
        self.config = config or OCRConfig()

    def _setup_tesseract(self):
        """Setup Tesseract configuration."""
        try:
            import pytesseract

            if self.config.tesseract_cmd:
                pytesseract.pytesseract.tesseract_cmd = self.config.tesseract_cmd

            return pytesseract
        except ImportError:
            raise ImportError("pytesseract not installed. Install with: pip install pytesseract")

    def _load_image(self, path: str):
        """Load an image for processing."""
        try:
            from PIL import Image

            return Image.open(path)
        except ImportError:
            raise ImportError("Pillow not installed. Install with: pip install pillow")

    async def extract_text(
        self,
        path: str,
        language: Optional[str] = None,
    ) -> OCRResult:
        """
        Extract text from an image.

        Args:
            path: Image file path
            language: Language code (e.g., 'eng', 'fra', 'deu')

        Returns:
            OCRResult with extracted text
        """
        loop = asyncio.get_running_loop()
        pytesseract = self._setup_tesseract()

        def _extract():
            image = self._load_image(path)
            lang = language or self.config.language

            # Get text
            text = pytesseract.image_to_string(
                image,
                lang=lang,
                config=f"--psm {self.config.psm} --oem {self.config.oem}",
            )

            # Get confidence
            data = pytesseract.image_to_data(
                image,
                lang=lang,
                output_type=pytesseract.Output.DICT,
            )

            confidences = [float(c) for c in data["conf"] if str(c) != "-1"]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0

            return OCRResult(
                text=text.strip(),
                confidence=avg_confidence,
                language=lang,
                source_path=path,
            )

        return await loop.run_in_executor(None, _extract)

    async def extract_with_boxes(
        self,
        path: str,
        language: Optional[str] = None,
        level: int = 5,  # Word level by default
    ) -> OCRResult:
        """
        Extract text with bounding boxes.

        Args:
            path: Image file path
            language: Language code
            level: Detail level (1=page to 5=word)

        Returns:
            OCRResult with boxes
        """
        loop = asyncio.get_running_loop()
        pytesseract = self._setup_tesseract()

        def _extract():
            image = self._load_image(path)
            lang = language or self.config.language

            data = pytesseract.image_to_data(
                image,
                lang=lang,
                output_type=pytesseract.Output.DICT,
                config=f"--psm {self.config.psm}",
            )

            boxes = []
            for i in range(len(data["text"])):
                if int(data["level"][i]) <= level and data["text"][i].strip():
                    conf = float(data["conf"][i])
                    if conf > 0:  # Filter out low confidence
                        boxes.append(
                            OCRBox(
                                text=data["text"][i],
                                confidence=conf,
                                x=int(data["left"][i]),
                                y=int(data["top"][i]),
                                width=int(data["width"][i]),
                                height=int(data["height"][i]),
                                level=int(data["level"][i]),
                            )
                        )

            full_text = " ".join(data["text"]).strip()
            confidences = [float(c) for c in data["conf"] if str(c) != "-1"]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0

            return OCRResult(
                text=full_text,
                boxes=boxes,
                confidence=avg_confidence,
                language=lang,
                source_path=path,
            )

        return await loop.run_in_executor(None, _extract)

    async def extract_to_searchable_pdf(
        self,
        input_path: str,
        output_path: str,
        language: Optional[str] = None,
    ) -> str:
        """
        Create searchable PDF from image.

        Args:
            input_path: Input image path
            output_path: Output PDF path
            language: Language code

        Returns:
            Output file path
        """
        loop = asyncio.get_running_loop()
        pytesseract = self._setup_tesseract()

        def _create():
            image = self._load_image(input_path)
            lang = language or self.config.language

            pdf_bytes = pytesseract.image_to_pdf_or_hocr(
                image,
                lang=lang,
                extension="pdf",
            )

            with open(output_path, "wb") as f:
                f.write(pdf_bytes)

            return output_path

        return await loop.run_in_executor(None, _create)

    async def batch_extract(
        self,
        paths: List[str],
        language: Optional[str] = None,
    ) -> List[OCRResult]:
        """
        Extract text from multiple images.

        Args:
            paths: List of image paths
            language: Language code

        Returns:
            List of OCRResults
        """
        tasks = [self.extract_text(path, language) for path in paths]
        return await asyncio.gather(*tasks)

    async def detect_orientation(
        self,
        path: str,
    ) -> Dict[str, Any]:
        """
        Detect image orientation and script.

        Args:
            path: Image file path

        Returns:
            Dict with orientation info
        """
        loop = asyncio.get_running_loop()
        pytesseract = self._setup_tesseract()

        def _detect():
            image = self._load_image(path)

            try:
                osd = pytesseract.image_to_osd(image, output_type=pytesseract.Output.DICT)
                return {
                    "orientation": osd.get("orientation", 0),
                    "rotate": osd.get("rotate", 0),
                    "script": osd.get("script", ""),
                    "confidence": osd.get("orientation_conf", 0),
                }
            except Exception as e:
                return {"error": str(e)}

        return await loop.run_in_executor(None, _detect)

    async def preprocess_image(
        self,
        path: str,
        output_path: str,
        deskew: bool = True,
        denoise: bool = True,
        binarize: bool = True,
    ) -> str:
        """
        Preprocess image for better OCR.

        Args:
            path: Input image path
            output_path: Output image path
            deskew: Apply deskew correction
            denoise: Apply noise reduction
            binarize: Convert to black and white

        Returns:
            Output file path
        """
        loop = asyncio.get_running_loop()

        def _preprocess():
            try:
                from PIL import Image, ImageFilter, ImageOps
                import numpy as np
            except ImportError:
                raise ImportError("Pillow not installed")

            image = Image.open(path)

            # Convert to grayscale
            if image.mode != "L":
                image = image.convert("L")

            if denoise:
                image = image.filter(ImageFilter.MedianFilter(size=3))

            if binarize:
                # Otsu's thresholding approximation
                image = image.point(lambda x: 0 if x < 128 else 255)

            if deskew:
                # Simple deskew based on rotation detection
                try:
                    pytesseract = self._setup_tesseract()
                    osd = pytesseract.image_to_osd(image, output_type=pytesseract.Output.DICT)
                    angle = osd.get("rotate", 0)
                    if angle:
                        image = image.rotate(-angle, expand=True, fillcolor=255)
                except Exception as e:
                    logger.debug("OCR deskew failed, proceeding without rotation: %s", e)

            image.save(output_path)
            return output_path

        return await loop.run_in_executor(None, _preprocess)

    def get_available_languages(self) -> List[str]:
        """Get list of available OCR languages."""
        pytesseract = self._setup_tesseract()
        try:
            return pytesseract.get_languages()
        except (OSError, RuntimeError) as e:
            logger.debug("Failed to enumerate OCR languages: %s", e)
            return ["eng"]
