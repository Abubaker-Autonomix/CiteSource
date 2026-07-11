"""
Recursive character chunker. No dependencies, no API keys.
Same approach as Task 9's crawler chunker.
"""


class RecursiveCharacterChunker:
    SEPARATORS = ["\n\n", "\n", ". ", " ", ""]

    def split(self, text: str, chunk_size: int = 800, chunk_overlap: int = 100) -> list[str]:
        return self._split(text, self.SEPARATORS, chunk_size, chunk_overlap)

    def _split(self, text: str, separators: list[str], chunk_size: int, chunk_overlap: int) -> list[str]:
        if len(text) <= chunk_size or not separators:
            return self._merge_with_overlap([text], chunk_size, chunk_overlap) if len(text) > chunk_size else [text]

        sep, rest_seps = separators[0], separators[1:]
        parts = text.split(sep) if sep else list(text)

        chunks = []
        current = ""
        for part in parts:
            candidate = current + sep + part if current else part
            if len(candidate) <= chunk_size:
                current = candidate
            else:
                if current:
                    chunks.append(current)
                if len(part) > chunk_size:
                    chunks.extend(self._split(part, rest_seps, chunk_size, chunk_overlap))
                    current = ""
                else:
                    current = part
        if current:
            chunks.append(current)

        return self._merge_with_overlap(chunks, chunk_size, chunk_overlap)

    def _merge_with_overlap(self, chunks: list[str], chunk_size: int, chunk_overlap: int) -> list[str]:
        if chunk_overlap <= 0 or len(chunks) <= 1:
            return [c.strip() for c in chunks if c.strip()]
        result = []
        for i, chunk in enumerate(chunks):
            if i > 0 and chunk_overlap > 0:
                prev_tail = chunks[i - 1][-chunk_overlap:]
                chunk = prev_tail + chunk
            result.append(chunk.strip())
        return [c for c in result if c]
