import re
from typing import Any, Dict, List


class TextChunker:
    """Sliding-window text chunker respecting paragraph and sentence boundaries."""

    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 120):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_text(self, text: str) -> List[Dict[str, Any]]:
        """Split text into overlapping semantic segments.
        
        Returns:
            List of dicts: {"index": int, "content": str, "token_count": int, "metadata": dict}
        """
        if not text or not text.strip():
            return []

        # 1. First split by double newlines (paragraphs)
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

        chunks = []
        current_chunk_parts = []
        current_length = 0

        for para in paragraphs:
            para_len = len(para)

            # If a single paragraph is larger than chunk_size, split by sentences
            if para_len > self.chunk_size:
                # Flush existing buffer first
                if current_chunk_parts:
                    chunk_str = "\n\n".join(current_chunk_parts)
                    chunks.append(chunk_str)
                    current_chunk_parts = []
                    current_length = 0

                sub_chunks = self._split_large_paragraph(para)
                chunks.extend(sub_chunks)
                continue

            # If adding this paragraph exceeds chunk_size, flush buffer
            if current_length + para_len + 2 > self.chunk_size and current_chunk_parts:
                chunk_str = "\n\n".join(current_chunk_parts)
                chunks.append(chunk_str)

                # Keep overlap from the end of current chunk if possible
                overlap_chars = 0
                overlap_parts = []
                for part in reversed(current_chunk_parts):
                    if overlap_chars + len(part) <= self.chunk_overlap:
                        overlap_parts.insert(0, part)
                        overlap_chars += len(part)
                    else:
                        break

                current_chunk_parts = overlap_parts
                current_length = sum(len(p) for p in current_chunk_parts)

            current_chunk_parts.append(para)
            current_length += para_len + 2

        # Flush remaining parts
        if current_chunk_parts:
            chunks.append("\n\n".join(current_chunk_parts))

        # Format with indexing and metadata
        result = []
        for idx, chunk_text in enumerate(chunks):
            words = chunk_text.split()
            token_est = int(len(words) * 1.3)
            result.append({
                "index": idx,
                "content": chunk_text,
                "token_count": token_est,
                "metadata": {
                    "char_length": len(chunk_text),
                    "word_count": len(words),
                    "chunk_index": idx,
                },
            })

        return result

    def _split_large_paragraph(self, paragraph: str) -> List[str]:
        """Split a long paragraph by sentence boundaries."""
        sentences = re.split(r"(?<=[.?!])\s+", paragraph)
        sub_chunks = []
        current_s = []
        current_len = 0

        for s in sentences:
            s_len = len(s)
            if current_len + s_len > self.chunk_size and current_s:
                sub_chunks.append(" ".join(current_s))
                current_s = []
                current_len = 0

            current_s.append(s)
            current_len += s_len + 1

        if current_s:
            sub_chunks.append(" ".join(current_s))

        return sub_chunks
