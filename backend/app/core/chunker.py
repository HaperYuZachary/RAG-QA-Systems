from dataclasses import dataclass
import re


DEFAULT_CHUNK_SIZE = 500
DEFAULT_CHUNK_OVERLAP = 50


@dataclass(frozen=True)
class Chunk:
    text: str
    chunk_index: int
    start_pos: int
    end_pos: int
    metadata: dict


@dataclass(frozen=True)
class TextBlock:
    text: str
    start_pos: int
    end_pos: int
    metadata: dict


def chunk_text(
    text: str,
    file_type: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[Chunk]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be non-negative and smaller than chunk_size")
    if not text.strip():
        return []

    normalized_type = file_type.lower()
    blocks = (
        _markdown_heading_blocks(text, normalized_type)
        if normalized_type in {"md", "markdown"}
        else []
    )
    if not blocks:
        blocks = _paragraph_blocks(text, normalized_type)
        return _reindex(
            _chunk_paragraph_blocks(
                blocks,
                text,
                0,
                chunk_size,
                overlap,
            )
        )

    chunks: list[Chunk] = []
    for block in blocks:
        if len(block.text) <= chunk_size:
            chunks.append(_to_chunk(block, len(chunks)))
            continue

        if block.metadata["strategy"] == "paragraph":
            chunks.extend(
                _chunk_paragraph_blocks(
                    _paragraph_blocks(block.text, normalized_type, block.start_pos),
                    text,
                    len(chunks),
                    chunk_size,
                    overlap,
                )
            )
        else:
            chunks.extend(
                _sliding_window_chunks(
                    block.text,
                    block.start_pos,
                    len(chunks),
                    chunk_size,
                    overlap,
                    {**block.metadata, "strategy": "sliding_window"},
                )
            )

    return _reindex(chunks)


def _markdown_heading_blocks(text: str, file_type: str) -> list[TextBlock]:
    headings = list(re.finditer(r"(?m)^#{1,6}\s+.+$", text))
    if not headings:
        return []

    blocks: list[TextBlock] = []

    # 补回第一个标题之前的导语，否则这段正文会被静默丢弃
    preamble, preamble_start, preamble_end = _trim_span(text, 0, headings[0].start())
    if preamble:
        blocks.append(
            TextBlock(
                text=preamble,
                start_pos=preamble_start,
                end_pos=preamble_end,
                metadata={"strategy": "paragraph", "file_type": file_type},
            )
        )

    for index, heading in enumerate(headings):
        block_start = heading.start()
        block_end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        block_text, start_pos, end_pos = _trim_span(text, block_start, block_end)
        if block_text:
            blocks.append(
                TextBlock(
                    text=block_text,
                    start_pos=start_pos,
                    end_pos=end_pos,
                    metadata={
                        "strategy": "structure",
                        "file_type": file_type,
                        "heading": heading.group().strip(),
                    },
                )
            )
    return blocks


def _paragraph_blocks(
    text: str,
    file_type: str,
    offset: int = 0,
) -> list[TextBlock]:
    blocks: list[TextBlock] = []
    for match in re.finditer(r"\S.*?(?=\n\s*\n|\Z)", text, flags=re.S):
        paragraph_text, start_pos, end_pos = _trim_span(
            text,
            match.start(),
            match.end(),
        )
        if paragraph_text:
            blocks.append(
                TextBlock(
                    text=paragraph_text,
                    start_pos=offset + start_pos,
                    end_pos=offset + end_pos,
                    metadata={"strategy": "paragraph", "file_type": file_type},
                )
            )
    return blocks


def _chunk_paragraph_blocks(
    blocks: list[TextBlock],
    source_text: str,
    start_index: int,
    chunk_size: int,
    overlap: int,
) -> list[Chunk]:
    chunks: list[Chunk] = []
    current_start: int | None = None
    current_end: int | None = None
    current_metadata: dict | None = None

    for block in blocks:
        if len(block.text) > chunk_size:
            if current_start is not None and current_end is not None and current_metadata:
                chunks.append(
                    Chunk(
                        text=source_text[current_start:current_end].strip(),
                        chunk_index=start_index + len(chunks),
                        start_pos=current_start,
                        end_pos=current_end,
                        metadata=current_metadata,
                    )
                )
                current_start = current_end = current_metadata = None

            chunks.extend(
                _sliding_window_chunks(
                    block.text,
                    block.start_pos,
                    start_index + len(chunks),
                    chunk_size,
                    overlap,
                    {**block.metadata, "strategy": "sliding_window"},
                )
            )
            continue

        if current_start is None:
            current_start = block.start_pos
            current_end = block.end_pos
            current_metadata = block.metadata
            continue

        candidate_text = source_text[current_start:block.end_pos].strip()
        if len(candidate_text) <= chunk_size:
            current_end = block.end_pos
        else:
            chunks.append(
                Chunk(
                    text=source_text[current_start:current_end].strip(),
                    chunk_index=start_index + len(chunks),
                    start_pos=current_start,
                    end_pos=current_end,
                    metadata=current_metadata or block.metadata,
                )
            )
            current_start = block.start_pos
            current_end = block.end_pos
            current_metadata = block.metadata

    if current_start is not None and current_end is not None and current_metadata:
        chunks.append(
            Chunk(
                text=source_text[current_start:current_end].strip(),
                chunk_index=start_index + len(chunks),
                start_pos=current_start,
                end_pos=current_end,
                metadata=current_metadata,
            )
        )
    return chunks


def _sliding_window_chunks(
    text: str,
    offset: int,
    start_index: int,
    chunk_size: int,
    overlap: int,
    metadata: dict,
) -> list[Chunk]:
    chunks: list[Chunk] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(
            Chunk(
                text=text[start:end],
                chunk_index=start_index + len(chunks),
                start_pos=offset + start,
                end_pos=offset + end,
                metadata=metadata,
            )
        )
        if end == len(text):
            break
        start = end - overlap
    return chunks


def _to_chunk(block: TextBlock, chunk_index: int) -> Chunk:
    return Chunk(
        text=block.text,
        chunk_index=chunk_index,
        start_pos=block.start_pos,
        end_pos=block.end_pos,
        metadata=block.metadata,
    )


def _trim_span(text: str, start: int, end: int) -> tuple[str, int, int]:
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return text[start:end], start, end


def _reindex(chunks: list[Chunk]) -> list[Chunk]:
    return [
        Chunk(
            text=chunk.text,
            chunk_index=index,
            start_pos=chunk.start_pos,
            end_pos=chunk.end_pos,
            metadata=chunk.metadata,
        )
        for index, chunk in enumerate(chunks)
    ]
