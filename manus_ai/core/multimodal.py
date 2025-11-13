"""
Multi-Modal Support for Chat
Handles images, PDFs, audio, and other file types in conversations
"""

import base64
import io
import logging
import mimetypes
from typing import Dict, Any, List, Optional, Union, BinaryIO
from dataclasses import dataclass
from pathlib import Path
from enum import Enum
import hashlib

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

try:
    import docx
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

logger = logging.getLogger(__name__)


class FileType(str, Enum):
    """Supported file types"""
    IMAGE = "image"
    PDF = "pdf"
    DOCUMENT = "document"
    AUDIO = "audio"
    VIDEO = "video"
    TEXT = "text"
    CODE = "code"
    SPREADSHEET = "spreadsheet"
    UNKNOWN = "unknown"


@dataclass
class MediaFile:
    """Represents a media file"""
    file_id: str
    file_type: FileType
    mime_type: str
    size_bytes: int
    filename: str
    content: Optional[bytes] = None
    text_content: Optional[str] = None
    metadata: Dict[str, Any] = None
    thumbnail: Optional[bytes] = None
    base64_data: Optional[str] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def get_base64(self) -> str:
        """Get base64 encoded content"""
        if self.base64_data:
            return self.base64_data
        if self.content:
            self.base64_data = base64.b64encode(self.content).decode('utf-8')
            return self.base64_data
        return ""

    def get_data_uri(self) -> str:
        """Get data URI for embedding"""
        return f"data:{self.mime_type};base64,{self.get_base64()}"


class FileProcessor:
    """Processes different file types"""

    SUPPORTED_MIME_TYPES = {
        # Images
        'image/jpeg': FileType.IMAGE,
        'image/png': FileType.IMAGE,
        'image/gif': FileType.IMAGE,
        'image/webp': FileType.IMAGE,
        'image/bmp': FileType.IMAGE,
        'image/svg+xml': FileType.IMAGE,
        # Documents
        'application/pdf': FileType.PDF,
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': FileType.DOCUMENT,
        'application/msword': FileType.DOCUMENT,
        'application/vnd.oasis.opendocument.text': FileType.DOCUMENT,
        # Text
        'text/plain': FileType.TEXT,
        'text/html': FileType.TEXT,
        'text/markdown': FileType.TEXT,
        'text/csv': FileType.TEXT,
        # Code
        'text/x-python': FileType.CODE,
        'text/javascript': FileType.CODE,
        'application/json': FileType.CODE,
        'application/xml': FileType.CODE,
        # Spreadsheets
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': FileType.SPREADSHEET,
        'application/vnd.ms-excel': FileType.SPREADSHEET,
        # Audio
        'audio/mpeg': FileType.AUDIO,
        'audio/wav': FileType.AUDIO,
        'audio/ogg': FileType.AUDIO,
        # Video
        'video/mp4': FileType.VIDEO,
        'video/webm': FileType.VIDEO,
        'video/ogg': FileType.VIDEO,
    }

    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB
    MAX_THUMBNAIL_SIZE = (256, 256)

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def _generate_file_id(self, content: bytes) -> str:
        """Generate unique file ID from content hash"""
        return hashlib.sha256(content).hexdigest()[:16]

    def detect_file_type(self, filename: str, content: bytes) -> tuple[FileType, str]:
        """
        Detect file type from filename and content

        Args:
            filename: Original filename
            content: File content bytes

        Returns:
            Tuple of (FileType, mime_type)
        """
        # Try to detect from filename
        mime_type, _ = mimetypes.guess_type(filename)

        if not mime_type:
            # Try to detect from content magic bytes
            mime_type = self._detect_from_magic_bytes(content)

        file_type = self.SUPPORTED_MIME_TYPES.get(mime_type, FileType.UNKNOWN)
        return file_type, mime_type or "application/octet-stream"

    def _detect_from_magic_bytes(self, content: bytes) -> Optional[str]:
        """Detect MIME type from magic bytes"""
        if not content:
            return None

        # Common magic bytes
        magic_bytes = {
            b'\xFF\xD8\xFF': 'image/jpeg',
            b'\x89PNG\r\n\x1a\n': 'image/png',
            b'GIF87a': 'image/gif',
            b'GIF89a': 'image/gif',
            b'%PDF': 'application/pdf',
            b'PK\x03\x04': 'application/zip',  # Also used by DOCX, XLSX
        }

        for magic, mime_type in magic_bytes.items():
            if content.startswith(magic):
                return mime_type

        return None

    async def process_file(
        self,
        filename: str,
        content: bytes,
        extract_text: bool = True,
        generate_thumbnail: bool = True
    ) -> MediaFile:
        """
        Process uploaded file

        Args:
            filename: Original filename
            content: File content
            extract_text: Whether to extract text content
            generate_thumbnail: Whether to generate thumbnail for images

        Returns:
            Processed MediaFile object
        """
        # Validate size
        if len(content) > self.MAX_FILE_SIZE:
            raise ValueError(f"File too large: {len(content)} bytes (max: {self.MAX_FILE_SIZE})")

        # Detect file type
        file_type, mime_type = self.detect_file_type(filename, content)
        file_id = self._generate_file_id(content)

        self.logger.info(f"Processing file: {filename} ({file_type.value}, {len(content)} bytes)")

        # Create media file
        media_file = MediaFile(
            file_id=file_id,
            file_type=file_type,
            mime_type=mime_type,
            size_bytes=len(content),
            filename=filename,
            content=content
        )

        # Extract text content based on file type
        if extract_text:
            if file_type == FileType.IMAGE:
                media_file.text_content = await self._extract_image_text(content, mime_type)
            elif file_type == FileType.PDF:
                media_file.text_content = await self._extract_pdf_text(content)
            elif file_type == FileType.DOCUMENT:
                media_file.text_content = await self._extract_document_text(content, filename)
            elif file_type in [FileType.TEXT, FileType.CODE]:
                try:
                    media_file.text_content = content.decode('utf-8')
                except UnicodeDecodeError:
                    self.logger.warning(f"Failed to decode text file: {filename}")

        # Generate thumbnail for images
        if generate_thumbnail and file_type == FileType.IMAGE:
            media_file.thumbnail = await self._generate_thumbnail(content)

        # Extract metadata
        media_file.metadata = await self._extract_metadata(media_file)

        return media_file

    async def _extract_image_text(self, content: bytes, mime_type: str) -> Optional[str]:
        """Extract text from image using OCR (placeholder)"""
        # TODO: Implement OCR using Tesseract or cloud OCR API
        self.logger.debug("Image text extraction not implemented yet")
        return None

    async def _extract_pdf_text(self, content: bytes) -> Optional[str]:
        """Extract text from PDF"""
        if not PDF_AVAILABLE:
            self.logger.warning("PyPDF2 not available for PDF text extraction")
            return None

        try:
            pdf_file = io.BytesIO(content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)

            text_parts = []
            for page_num, page in enumerate(pdf_reader.pages):
                try:
                    text = page.extract_text()
                    if text.strip():
                        text_parts.append(f"--- Page {page_num + 1} ---\n{text}")
                except Exception as e:
                    self.logger.warning(f"Failed to extract text from page {page_num + 1}: {e}")

            return "\n\n".join(text_parts)

        except Exception as e:
            self.logger.error(f"PDF text extraction failed: {e}")
            return None

    async def _extract_document_text(self, content: bytes, filename: str) -> Optional[str]:
        """Extract text from Word documents"""
        if filename.endswith('.docx') and DOCX_AVAILABLE:
            try:
                doc_file = io.BytesIO(content)
                doc = docx.Document(doc_file)
                paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
                return "\n\n".join(paragraphs)
            except Exception as e:
                self.logger.error(f"DOCX text extraction failed: {e}")

        return None

    async def _generate_thumbnail(self, content: bytes) -> Optional[bytes]:
        """Generate thumbnail for image"""
        if not PIL_AVAILABLE:
            return None

        try:
            image = Image.open(io.BytesIO(content))
            image.thumbnail(self.MAX_THUMBNAIL_SIZE, Image.Resampling.LANCZOS)

            # Convert to bytes
            thumb_io = io.BytesIO()
            image.save(thumb_io, format='PNG')
            return thumb_io.getvalue()

        except Exception as e:
            self.logger.error(f"Thumbnail generation failed: {e}")
            return None

    async def _extract_metadata(self, media_file: MediaFile) -> Dict[str, Any]:
        """Extract metadata from file"""
        metadata = {
            "file_id": media_file.file_id,
            "filename": media_file.filename,
            "size_bytes": media_file.size_bytes,
            "mime_type": media_file.mime_type,
            "file_type": media_file.file_type.value
        }

        # Image-specific metadata
        if media_file.file_type == FileType.IMAGE and PIL_AVAILABLE:
            try:
                image = Image.open(io.BytesIO(media_file.content))
                metadata.update({
                    "width": image.width,
                    "height": image.height,
                    "format": image.format,
                    "mode": image.mode
                })
            except Exception as e:
                self.logger.warning(f"Failed to extract image metadata: {e}")

        # PDF-specific metadata
        elif media_file.file_type == FileType.PDF and PDF_AVAILABLE:
            try:
                pdf_file = io.BytesIO(media_file.content)
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                metadata.update({
                    "page_count": len(pdf_reader.pages),
                    "pdf_metadata": dict(pdf_reader.metadata) if pdf_reader.metadata else {}
                })
            except Exception as e:
                self.logger.warning(f"Failed to extract PDF metadata: {e}")

        return metadata


class MultiModalManager:
    """Manages multi-modal content in conversations"""

    def __init__(self, storage_backend: Optional[Any] = None):
        """
        Initialize multi-modal manager

        Args:
            storage_backend: Optional storage for files
        """
        self.processor = FileProcessor()
        self.storage = storage_backend
        self.files: Dict[str, MediaFile] = {}
        self.logger = logging.getLogger(__name__)

    async def upload_file(
        self,
        filename: str,
        content: bytes,
        session_id: Optional[str] = None
    ) -> MediaFile:
        """
        Upload and process file

        Args:
            filename: Original filename
            content: File content
            session_id: Optional session ID for organization

        Returns:
            Processed MediaFile
        """
        # Process file
        media_file = await self.processor.process_file(filename, content)

        # Store in memory
        self.files[media_file.file_id] = media_file

        # Persist to storage if available
        if self.storage:
            await self._persist_file(media_file, session_id)

        self.logger.info(f"Uploaded file: {filename} (ID: {media_file.file_id})")
        return media_file

    async def get_file(self, file_id: str) -> Optional[MediaFile]:
        """Get file by ID"""
        return self.files.get(file_id)

    async def delete_file(self, file_id: str) -> bool:
        """Delete file"""
        if file_id in self.files:
            del self.files[file_id]
            if self.storage:
                await self._delete_from_storage(file_id)
            return True
        return False

    async def _persist_file(self, media_file: MediaFile, session_id: Optional[str]):
        """Persist file to storage"""
        # Implement storage-specific logic
        pass

    async def _delete_from_storage(self, file_id: str):
        """Delete file from storage"""
        # Implement storage-specific logic
        pass

    def format_for_llm(self, media_file: MediaFile) -> Dict[str, Any]:
        """
        Format media file for LLM consumption

        Args:
            media_file: Media file to format

        Returns:
            Dictionary formatted for LLM input
        """
        # For images, include base64 data
        if media_file.file_type == FileType.IMAGE:
            return {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_file.mime_type,
                    "data": media_file.get_base64()
                }
            }

        # For text-based files, include extracted text
        elif media_file.text_content:
            return {
                "type": "document",
                "filename": media_file.filename,
                "content": media_file.text_content,
                "metadata": media_file.metadata
            }

        # For other files, include metadata only
        else:
            return {
                "type": "file",
                "filename": media_file.filename,
                "file_type": media_file.file_type.value,
                "metadata": media_file.metadata
            }

    async def get_session_files(self, session_id: str) -> List[MediaFile]:
        """Get all files for a session"""
        # This would query storage backend in production
        return [f for f in self.files.values()]
