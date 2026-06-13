from app.core.chunker import Chunk, chunk_text


def test_markdown_headings_create_structure_aware_chunks():
    text = (
        "# Employee Handbook\n"
        "Company-wide rules.\n\n"
        "## Annual Leave\n"
        "Employees with 1-10 years receive 5 days.\n\n"
        "## Reimbursement\n"
        "Taxi receipts require manager approval."
    )

    chunks = chunk_text(text, file_type="md", chunk_size=120, overlap=20)

    assert [chunk.text.splitlines()[0] for chunk in chunks] == [
        "# Employee Handbook",
        "## Annual Leave",
        "## Reimbursement",
    ]
    assert chunks[1].metadata["heading"] == "## Annual Leave"
    assert chunks[1].metadata["strategy"] == "structure"


def test_paragraphs_are_merged_on_natural_boundaries():
    text = (
        "Alpha policy paragraph.\n\n"
        "Beta policy paragraph.\n\n"
        "Gamma policy paragraph is longer and should stand alone."
    )

    chunks = chunk_text(text, file_type="docx", chunk_size=70, overlap=10)

    assert [chunk.text for chunk in chunks] == [
        "Alpha policy paragraph.\n\nBeta policy paragraph.",
        "Gamma policy paragraph is longer and should stand alone.",
    ]
    assert all("\n\n" not in chunk.text.strip("\n").splitlines()[0] for chunk in chunks)
    assert chunks[0].metadata["strategy"] == "paragraph"


def test_long_text_uses_sliding_window_with_overlap():
    text = "0123456789" * 30

    chunks = chunk_text(text, file_type="pdf", chunk_size=100, overlap=20)

    assert len(chunks) == 4
    assert all(len(chunk.text) <= 100 for chunk in chunks)
    assert chunks[1].text.startswith(chunks[0].text[-20:])
    assert chunks[1].start_pos == chunks[0].end_pos - 20
    assert chunks[0].metadata["strategy"] == "sliding_window"


def test_default_chunk_size_and_overlap_are_500_and_50():
    text = "x" * 1200

    chunks = chunk_text(text, file_type="pdf")

    assert [len(chunk.text) for chunk in chunks] == [500, 500, 300]
    assert chunks[1].start_pos == 450
    assert chunks[2].start_pos == 900


def test_long_markdown_section_keeps_heading_metadata_with_sliding_fallback():
    text = "# Long Policy\n" + ("policy detail " * 80)

    chunks = chunk_text(text, file_type="md", chunk_size=120, overlap=30)

    assert len(chunks) > 1
    assert all(len(chunk.text) <= 120 for chunk in chunks)
    assert all(chunk.metadata["heading"] == "# Long Policy" for chunk in chunks)
    assert all(chunk.metadata["strategy"] == "sliding_window" for chunk in chunks)


def test_markdown_preamble_before_first_heading_is_not_dropped():
    text = (
        "This intro applies to all employees.\n\n"
        "# Annual Leave\n"
        "Employees with 1-10 years receive 5 days."
    )

    chunks = chunk_text(text, file_type="md", chunk_size=120, overlap=20)

    joined = "\n".join(chunk.text for chunk in chunks)
    assert "This intro applies to all employees." in joined
    assert chunks[0].text == "This intro applies to all employees."
    assert chunks[0].metadata["strategy"] == "paragraph"
    assert chunks[0].start_pos == 0


def test_chunks_include_index_and_source_positions():
    text = "First paragraph.\n\nSecond paragraph."

    chunks = chunk_text(text, file_type="md", chunk_size=500, overlap=50)

    assert chunks == [
        Chunk(
            text=text,
            chunk_index=0,
            start_pos=0,
            end_pos=len(text),
            metadata={"strategy": "paragraph", "file_type": "md"},
        )
    ]
