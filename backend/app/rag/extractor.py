import csv
import io
import json
import logging
import os
import re
from typing import Any, Dict, Tuple

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf", ".json", ".csv"}
SUPPORTED_MIME_TYPES = {
    "text/plain",
    "text/markdown",
    "application/pdf",
    "application/json",
    "text/csv",
    "application/vnd.ms-excel",
}


def sanitize_filename(filename: str) -> str:
    """Sanitize client-provided filename, stripping directory paths and non-safe characters."""
    base = os.path.basename(filename)
    # Remove null bytes and control characters
    base = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", base)
    # Remove path traversal characters
    base = base.replace("..", "").replace("/", "").replace("\\", "")
    # Default if empty
    return base.strip() or "untitled_document"


def validate_file_safety(file_path: str, allowed_base_dir: str) -> bool:
    """Ensure file path is strictly within the allowed directory and prevents traversal."""
    resolved_file = os.path.abspath(file_path)
    resolved_base = os.path.abspath(allowed_base_dir)
    return resolved_file.startswith(resolved_base + os.path.sep)


class DocumentExtractor:
    """Secure text extraction service for PDFs, Markdown, TXT, CSV, and JSON."""

    @classmethod
    def extract_text_from_file(
        cls, file_path: str, mime_type: Optional[str] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """Extract text and metadata from physical file on disk."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found at path: {file_path}")

        ext = os.path.splitext(file_path)[1].lower()
        metadata: Dict[str, Any] = {"file_extension": ext}

        if ext == ".pdf":
            return cls._extract_pdf(file_path, metadata)
        elif ext in (".txt", ".md"):
            return cls._extract_text(file_path, metadata)
        elif ext == ".csv":
            return cls._extract_csv(file_path, metadata)
        elif ext == ".json":
            return cls._extract_json(file_path, metadata)
        else:
            # Fallback text attempt
            return cls._extract_text(file_path, metadata)

    @staticmethod
    def _extract_pdf(file_path: str, metadata: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """Extract text from PDF pages using pypdf."""
        import pypdf

        extracted_pages = []
        with open(file_path, "rb") as f:
            reader = pypdf.PdfReader(f)
            num_pages = len(reader.pages)
            metadata["page_count"] = num_pages

            for page_num, page in enumerate(reader.pages):
                page_text = page.extract_text() or ""
                if page_text.strip():
                    extracted_pages.append(page_text.strip())

        full_text = "\n\n".join(extracted_pages)
        metadata["extracted_pages"] = len(extracted_pages)
        return full_text, metadata

    @staticmethod
    def _extract_text(file_path: str, metadata: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """Extract plain text / markdown file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            with open(file_path, "r", encoding="latin-1") as f:
                content = f.read()

        metadata["line_count"] = len(content.splitlines())
        return content, metadata

    @staticmethod
    def _extract_csv(file_path: str, metadata: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """Extract structured tabular text from CSV."""
        lines = []
        try:
            with open(file_path, "r", encoding="utf-8", newline="") as f:
                reader = csv.reader(f)
                headers = next(reader, None)
                if headers:
                    lines.append(f"Columns: {', '.join(headers)}")
                row_count = 0
                for row in reader:
                    if any(row):
                        row_count += 1
                        if headers and len(headers) == len(row):
                            pairs = [f"{h}: {v}" for h, v in zip(headers, row) if v.strip()]
                            lines.append(" | ".join(pairs))
                        else:
                            lines.append(" | ".join(row))
                metadata["csv_rows"] = row_count
        except Exception as e:
            logger.warning("Error parsing CSV: %s. Falling back to plain text.", e)
            return DocumentExtractor._extract_text(file_path, metadata)

        return "\n".join(lines), metadata

    @staticmethod
    def _extract_json(file_path: str, metadata: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """Extract structured JSON formatted for LLM ingestion."""
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, list):
            metadata["json_items"] = len(data)
            lines = [json.dumps(item, indent=2) for item in data]
            return "\n\n".join(lines), metadata
        elif isinstance(data, dict):
            metadata["json_keys"] = list(data.keys())
            return json.dumps(data, indent=2), metadata
        else:
            return str(data), metadata
