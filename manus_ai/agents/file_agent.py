"""
File Processing Agent - Handles file operations, format conversion, and document generation
"""

import logging
from typing import Dict, Any, List, Optional
import mimetypes
import json

from .base_agent import BaseAgent
from ..core.llm_providers import LLMProvider

logger = logging.getLogger(__name__)


class FileProcessingAgent(BaseAgent):
    """
    Specialized agent for file processing
    Capabilities:
    - File format conversion
    - Document generation (PDF, DOCX, etc.)
    - Image processing
    - File parsing and extraction
    - Batch file operations
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.agent_type = "file"
        self.default_provider = LLMProvider.CLAUDE_SONNET_4_5
        self.capabilities = [
            "format_conversion",
            "document_generation",
            "image_processing",
            "pdf_generation",
            "excel_generation",
            "file_parsing",
            "batch_operations"
        ]
        self.supported_formats = {
            "documents": ["pdf", "docx", "txt", "md", "html"],
            "spreadsheets": ["xlsx", "csv", "json"],
            "images": ["png", "jpg", "jpeg", "gif", "svg"],
            "presentations": ["pptx"],
            "data": ["json", "xml", "yaml", "csv"]
        }

    async def execute(self, task: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute file processing task"""
        self.log_execution(task.id, f"Starting file processing: {task.title}")

        try:
            # Determine operation type
            operation = await self._determine_operation(task)

            # Execute appropriate file operation
            if operation == "conversion":
                result = await self._convert_file(task, context)
            elif operation == "generation":
                result = await self._generate_document(task, context)
            elif operation == "parsing":
                result = await self._parse_file(task, context)
            elif operation == "batch":
                result = await self._batch_operation(task, context)
            else:
                result = await self._general_file_operation(task, context)

            self.log_execution(task.id, "File processing completed successfully")

            return result

        except Exception as e:
            self.log_execution(task.id, f"File processing failed: {e}", "error")
            raise

    async def _determine_operation(self, task: Any) -> str:
        """Determine type of file operation"""
        description = task.description.lower()

        if any(kw in description for kw in ["convert", "transform", "change format"]):
            return "conversion"
        elif any(kw in description for kw in ["generate", "create", "build", "produce"]):
            return "generation"
        elif any(kw in description for kw in ["parse", "extract", "read"]):
            return "parsing"
        elif any(kw in description for kw in ["batch", "multiple", "all files"]):
            return "batch"
        else:
            return "general"

    async def _convert_file(self, task: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """Convert file from one format to another"""
        convert_prompt = f"""Create file conversion code.

Task: {task.description}

Provide Python code to:
1. Read the source file format
2. Parse/process the content
3. Convert to target format
4. Handle any format-specific requirements
5. Preserve data integrity
6. Handle errors gracefully

Use appropriate libraries (pypdf2, python-docx, pandas, Pillow, etc.)"""

        messages = [
            {"role": "system", "content": "You are an expert in file format conversion."},
            {"role": "user", "content": convert_prompt}
        ]

        response = await self.generate_response(
            messages=messages,
            provider=self.default_provider,
            temperature=0.2
        )

        return {
            "type": "file_conversion",
            "code": response["content"],
            "note": "Execute code with actual files to perform conversion"
        }

    async def _generate_document(self, task: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate document (PDF, DOCX, PPTX, etc.)"""
        gen_prompt = f"""Create document generation code.

Task: {task.description}

Provide Python code to:
1. Create the document structure
2. Add content (text, tables, images, etc.)
3. Apply formatting and styling
4. Generate the final document
5. Save in requested format

Use libraries like reportlab, python-docx, python-pptx, etc.
Make output professional and well-formatted."""

        messages = [
            {"role": "system", "content": "You are an expert in programmatic document generation."},
            {"role": "user", "content": gen_prompt}
        ]

        response = await self.generate_response(
            messages=messages,
            provider=self.default_provider,
            temperature=0.3
        )

        return {
            "type": "document_generation",
            "code": response["content"],
            "format": self._detect_output_format(task.description)
        }

    async def _parse_file(self, task: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """Parse and extract data from file"""
        parse_prompt = f"""Create file parsing code.

Task: {task.description}

Provide Python code to:
1. Read the file
2. Parse the content structure
3. Extract relevant data
4. Structure the output
5. Handle malformed data
6. Return structured results

Use appropriate parsing libraries."""

        messages = [
            {"role": "system", "content": "You are an expert in file parsing and data extraction."},
            {"role": "user", "content": parse_prompt}
        ]

        response = await self.generate_response(
            messages=messages,
            provider=self.default_provider,
            temperature=0.2
        )

        return {
            "type": "file_parsing",
            "code": response["content"]
        }

    async def _batch_operation(self, task: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """Perform batch file operations"""
        batch_prompt = f"""Create batch file processing code.

Task: {task.description}

Provide Python code to:
1. Iterate through multiple files
2. Apply operation to each file
3. Handle errors for individual files
4. Track progress
5. Generate summary report
6. Implement parallel processing if appropriate

Make it robust and efficient."""

        messages = [
            {"role": "system", "content": "You are an expert in batch file processing."},
            {"role": "user", "content": batch_prompt}
        ]

        response = await self.generate_response(
            messages=messages,
            provider=self.default_provider,
            temperature=0.3
        )

        return {
            "type": "batch_operation",
            "code": response["content"]
        }

    async def _general_file_operation(self, task: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle general file operations"""
        messages = [
            {"role": "system", "content": "You are a file processing expert."},
            {"role": "user", "content": task.description}
        ]

        response = await self.generate_response(
            messages=messages,
            provider=self.default_provider,
            temperature=0.4
        )

        return {
            "type": "general_file_operation",
            "result": response["content"]
        }

    def _detect_output_format(self, description: str) -> str:
        """Detect desired output format"""
        formats = ["pdf", "docx", "xlsx", "pptx", "html", "md", "txt"]

        description_lower = description.lower()
        for fmt in formats:
            if fmt in description_lower:
                return fmt

        return "unknown"

    async def generate_presentation(
        self,
        topic: str,
        num_slides: int = 10
    ) -> Dict[str, Any]:
        """Generate PowerPoint presentation from topic"""
        ppt_prompt = f"""Create Python code to generate a PowerPoint presentation.

Topic: {topic}
Number of slides: {num_slides}

The code should:
1. Create a presentation with {num_slides} slides
2. Include title slide
3. Generate content slides with appropriate topics
4. Add bullet points, images placeholders
5. Use professional design
6. Save as .pptx file

Use python-pptx library."""

        messages = [
            {"role": "system", "content": "You are an expert in creating presentations programmatically."},
            {"role": "user", "content": ppt_prompt}
        ]

        response = await self.generate_response(
            messages=messages,
            provider=self.default_provider,
            temperature=0.4
        )

        return {
            "type": "presentation_generation",
            "topic": topic,
            "slides": num_slides,
            "code": response["content"]
        }

    async def generate_website(
        self,
        description: str,
        requirements: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate complete website (HTML/CSS/JS)"""
        web_prompt = f"""Create a complete, functional website.

Description: {description}
Requirements: {json.dumps(requirements or {}, indent=2)}

Generate:
1. HTML structure
2. CSS styling (responsive, modern)
3. JavaScript functionality
4. All necessary files
5. Make it production-ready

Create a professional, modern website."""

        messages = [
            {"role": "system", "content": "You are an expert web developer creating production-ready websites."},
            {"role": "user", "content": web_prompt}
        ]

        response = await self.generate_response(
            messages=messages,
            provider=self.default_provider,
            temperature=0.5,
            max_tokens=8000
        )

        return {
            "type": "website_generation",
            "files": self._extract_web_files(response["content"]),
            "full_response": response["content"]
        }

    def _extract_web_files(self, content: str) -> Dict[str, str]:
        """Extract individual web files from response"""
        files = {}

        # Simple extraction - in production would be more sophisticated
        if "<!DOCTYPE html>" in content or "<html>" in content:
            files["index.html"] = content

        return files
