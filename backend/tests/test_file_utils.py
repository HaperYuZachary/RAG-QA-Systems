import hashlib

import pytest

from app.utils.file_utils import (
    UnsupportedFileTypeError,
    calculate_sha256,
    detect_file_type,
)


def test_calculate_sha256_reads_file_bytes(tmp_path):
    file_path = tmp_path / "sample.md"
    file_content = b"# RAG\nKnowledge base"
    file_path.write_bytes(file_content)

    assert calculate_sha256(file_path) == hashlib.sha256(file_content).hexdigest()


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        ("policy.PDF", "pdf"),
        ("handbook.docx", "docx"),
        ("notes.md", "md"),
        ("README.markdown", "md"),
    ],
)
def test_detect_file_type_supports_ingestion_formats(filename, expected):
    assert detect_file_type(filename) == expected


def test_detect_file_type_rejects_unsupported_extensions():
    with pytest.raises(UnsupportedFileTypeError):
        detect_file_type("archive.zip")
