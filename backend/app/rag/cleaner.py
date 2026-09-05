import re
import unicodedata


class TextCleaner:
    """Text normalization and sanitization utilities for RAG ingestion."""

    @staticmethod
    def clean_text(raw_text: str) -> str:
        """Clean and normalize extracted document text."""
        if not raw_text:
            return ""

        # 1. Unicode NFKC normalization
        text = unicodedata.normalize("NFKC", raw_text)

        # 2. Replace null bytes and non-printable control characters (preserve \n, \r, \t)
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", text)

        # 3. Standardize Windows \r\n and classic Mac \r line breaks to Unix \n
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # 4. Collapse multiple horizontal whitespace characters (spaces, tabs) to single space
        text = re.sub(r"[ \t]+", " ", text)

        # 5. Strip trailing and leading whitespace on each line
        lines = [line.strip() for line in text.split("\n")]

        # 6. Collapse consecutive blank lines (limit to max 2 blank lines)
        cleaned_lines = []
        consecutive_blanks = 0
        for line in lines:
            if not line:
                consecutive_blanks += 1
                if consecutive_blanks <= 2:
                    cleaned_lines.append("")
            else:
                consecutive_blanks = 0
                cleaned_lines.append(line)

        return "\n".join(cleaned_lines).strip()
