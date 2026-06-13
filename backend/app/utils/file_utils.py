import hashlib
from pathlib import Path


class UnsupportedFileTypeError(ValueError):
    pass


SUPPORTED_FILE_TYPES = {
    ".pdf": "pdf",
    ".docx": "docx",
    ".md": "md",
    ".markdown": "md",
}


def calculate_sha256(path: str | Path) -> str:
    file_path = Path(path)
    digest = hashlib.sha256()

    with file_path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def detect_file_type(filename: str | Path) -> str:
    suffix = Path(filename).suffix.lower()
    try:
        return SUPPORTED_FILE_TYPES[suffix]
    except KeyError as exc:
        raise UnsupportedFileTypeError(
            f"Unsupported file type: {suffix or '<none>'}"
        ) from exc
