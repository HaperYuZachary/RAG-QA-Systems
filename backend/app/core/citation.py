from collections.abc import Sequence
from dataclasses import dataclass, field
import re
from typing import Any


CITATION_PATTERN = re.compile(r"\[(\d+)\]")


@dataclass(frozen=True)
class CitationSource:
    index: int
    id: str
    text: str
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class CitationResult:
    answer: str
    sources: list[CitationSource]
    referenced_indexes: list[int]
    invalid_references: list[int]


def resolve_citations(answer: str, candidates: Sequence[Any]) -> CitationResult:
    candidate_list = list(candidates)
    referenced_indexes: list[int] = []
    invalid_references: list[int] = []

    def replace_invalid(match: re.Match) -> str:
        index = int(match.group(1))
        if 1 <= index <= len(candidate_list):
            _append_unique(referenced_indexes, index)
            return match.group(0)

        _append_unique(invalid_references, index)
        return ""

    validated_answer = CITATION_PATTERN.sub(replace_invalid, answer)
    sources = [
        _candidate_to_source(index, candidate_list[index - 1])
        for index in referenced_indexes
    ]

    return CitationResult(
        answer=validated_answer,
        sources=sources,
        referenced_indexes=referenced_indexes,
        invalid_references=invalid_references,
    )


def _candidate_to_source(index: int, candidate: Any) -> CitationSource:
    return CitationSource(
        index=index,
        id=str(_read_candidate_value(candidate, "id", "")),
        text=str(_read_candidate_value(candidate, "text", "")),
        metadata=dict(_read_candidate_value(candidate, "metadata", {}) or {}),
    )


def _read_candidate_value(candidate: Any, name: str, default):
    if isinstance(candidate, dict):
        return candidate.get(name, default)
    return getattr(candidate, name, default)


def _append_unique(values: list[int], value: int) -> None:
    if value not in values:
        values.append(value)
