from dataclasses import dataclass

from app.core.citation import resolve_citations


@dataclass
class Candidate:
    id: str
    text: str
    metadata: dict


def test_resolve_citations_maps_numbered_references_to_candidates():
    candidates = [
        Candidate("chunk_1", "员工满一年享有五天年假。", {"document_id": "doc_1"}),
        Candidate("chunk_2", "报销需要提交发票。", {"document_id": "doc_2"}),
    ]

    result = resolve_citations(
        "员工满一年有五天年假[1]，报销要发票[2]。",
        candidates,
    )

    assert result.answer == "员工满一年有五天年假[1]，报销要发票[2]。"
    assert result.referenced_indexes == [1, 2]
    assert result.invalid_references == []
    assert [source.index for source in result.sources] == [1, 2]
    assert [source.id for source in result.sources] == ["chunk_1", "chunk_2"]
    assert result.sources[0].text == "员工满一年享有五天年假。"
    assert result.sources[0].metadata == {"document_id": "doc_1"}


def test_resolve_citations_deduplicates_sources_in_first_seen_order():
    candidates = [
        Candidate("chunk_1", "年假政策。", {}),
        Candidate("chunk_2", "报销政策。", {}),
    ]

    result = resolve_citations("先看年假[1]，再看年假[1]和报销[2]。", candidates)

    assert result.referenced_indexes == [1, 2]
    assert [source.id for source in result.sources] == ["chunk_1", "chunk_2"]


def test_resolve_citations_filters_hallucinated_references_from_answer():
    candidates = [
        Candidate("chunk_1", "年假政策。", {"page": 1}),
        Candidate("chunk_2", "报销政策。", {"page": 2}),
    ]

    result = resolve_citations("年假有说明[1][99]，不存在零号[0]。", candidates)

    assert result.answer == "年假有说明[1]，不存在零号。"
    assert result.referenced_indexes == [1]
    assert result.invalid_references == [99, 0]
    assert [source.id for source in result.sources] == ["chunk_1"]


def test_resolve_citations_accepts_dict_candidates():
    candidates = [
        {
            "id": "chunk_dict",
            "text": "字典候选内容。",
            "metadata": {"chunk_index": 0},
        }
    ]

    result = resolve_citations("答案来自字典候选[1]。", candidates)

    assert result.sources[0].id == "chunk_dict"
    assert result.sources[0].text == "字典候选内容。"
    assert result.sources[0].metadata == {"chunk_index": 0}


def test_resolve_citations_returns_empty_sources_when_answer_has_no_citations():
    result = resolve_citations("没有引用编号。", [Candidate("chunk_1", "内容。", {})])

    assert result.answer == "没有引用编号。"
    assert result.sources == []
    assert result.referenced_indexes == []
    assert result.invalid_references == []
