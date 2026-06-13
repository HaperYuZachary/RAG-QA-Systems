from contextlib import closing
import json

from app.config import Settings
from app.core.retriever import RetrievalResult
from app.db.sqlite_client import get_connection, init_db
from app.services.chat_service import ChatService


class FakeEmbedder:
    def __init__(self):
        self.calls = []

    def embed(self, texts):
        self.calls.append(list(texts))
        return [[0.1, 0.2, 0.3] for _ in texts]


class FakeRetriever:
    def __init__(self):
        self.calls = []
        self.candidates = [
            RetrievalResult(
                id="chunk_a",
                text="员工满一年享有五天年假。",
                metadata={"document_id": "doc_a", "chunk_index": 0},
                rrf_score=0.3,
            ),
            RetrievalResult(
                id="chunk_b",
                text="报销需要提交发票。",
                metadata={"document_id": "doc_b", "chunk_index": 1},
                rrf_score=0.2,
            ),
            RetrievalResult(
                id="chunk_c",
                text="年假余额可以在人事系统查看。",
                metadata={"document_id": "doc_c", "chunk_index": 2},
                rrf_score=0.1,
            ),
        ]

    def retrieve(self, kb_id, query, query_embedding):
        self.calls.append(
            {
                "kb_id": kb_id,
                "query": query,
                "query_embedding": query_embedding,
            }
        )
        return list(self.candidates)


class FakeReranker:
    def __init__(self):
        self.calls = []

    def rerank(self, query, candidates):
        candidate_list = list(candidates)
        self.calls.append({"query": query, "candidates": candidate_list})
        return [candidate_list[2], candidate_list[0]]


class FakeGenerator:
    def __init__(self, tokens):
        self.tokens = tokens
        self.calls = []

    def stream_chat(self, question, contexts, history=None):
        context_list = list(contexts)
        self.calls.append(
            {
                "question": question,
                "contexts": context_list,
                "history": list(history or []),
            }
        )
        yield from self.tokens


class FixedIds:
    def __init__(self):
        self.counts = {}

    def __call__(self, prefix):
        next_value = self.counts.get(prefix, 0) + 1
        self.counts[prefix] = next_value
        return f"{prefix}_{next_value}"


def seed_kb(settings: Settings, kb_id: str = "kb_1") -> None:
    with closing(get_connection(settings)) as conn, conn:
        conn.execute(
            """
            INSERT INTO knowledge_bases (id, name, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            """,
            (kb_id, "Default", "2026-06-10T00:00:00", "2026-06-10T00:00:00"),
        )


def fetch_rows(settings: Settings, table: str):
    with closing(get_connection(settings)) as conn, conn:
        return conn.execute(f"SELECT * FROM {table} ORDER BY created_at, id").fetchall()


def test_chat_service_streams_answer_resolves_sources_and_persists_messages(tmp_path):
    settings = Settings(data_dir=str(tmp_path))
    init_db(settings)
    seed_kb(settings)
    embedder = FakeEmbedder()
    retriever = FakeRetriever()
    reranker = FakeReranker()
    generator = FakeGenerator(["答案来自", "[1]", "，无效", "[3]"])
    service = ChatService(
        settings,
        embedder=embedder,
        retriever=retriever,
        reranker=reranker,
        generator=generator,
        id_factory=FixedIds(),
    )

    events = list(service.stream_chat("kb_1", "年假在哪里查？"))

    assert [event.event for event in events] == [
        "chunk",
        "chunk",
        "chunk",
        "chunk",
        "sources",
        "done",
    ]
    assert [event.data.get("delta") for event in events[:4]] == [
        "答案来自",
        "[1]",
        "，无效",
        "[3]",
    ]
    assert events[-2].data["sources"][0]["id"] == "chunk_c"
    assert events[-2].data["invalid_references"] == [3]
    assert events[-1].data["conversation_id"] == "conv_1"
    assert events[-1].data["answer"] == "答案来自[1]，无效"

    assert embedder.calls == [["年假在哪里查？"]]
    assert retriever.calls == [
        {
            "kb_id": "kb_1",
            "query": "年假在哪里查？",
            "query_embedding": [0.1, 0.2, 0.3],
        }
    ]
    assert [candidate.id for candidate in reranker.calls[0]["candidates"]] == [
        "chunk_a",
        "chunk_b",
        "chunk_c",
    ]
    assert [context.id for context in generator.calls[0]["contexts"]] == [
        "chunk_c",
        "chunk_a",
    ]
    # 新会话没有历史
    assert generator.calls[0]["history"] == []

    conversations = fetch_rows(settings, "conversations")
    assert len(conversations) == 1
    assert conversations[0]["id"] == "conv_1"
    assert conversations[0]["kb_id"] == "kb_1"
    assert conversations[0]["title"] == "年假在哪里查？"

    messages = fetch_rows(settings, "messages")
    assert [(row["id"], row["role"], row["content"]) for row in messages] == [
        ("msg_1", "user", "年假在哪里查？"),
        ("msg_2", "assistant", "答案来自[1]，无效"),
    ]
    assistant_sources = json.loads(messages[1]["sources"])
    assert assistant_sources["invalid_references"] == [3]
    assert assistant_sources["sources"][0]["id"] == "chunk_c"


def test_chat_service_feeds_prior_messages_to_generator_as_history(tmp_path):
    settings = Settings(data_dir=str(tmp_path))
    init_db(settings)
    seed_kb(settings)
    with closing(get_connection(settings)) as conn, conn:
        conn.execute(
            """
            INSERT INTO conversations (id, kb_id, title, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("conv_x", "kb_1", "Multi-turn", "2026-06-10T00:00:00", "2026-06-10T00:00:00"),
        )
        conn.execute(
            """
            INSERT INTO messages
                (id, conversation_id, role, content, sources, token_count, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            ("m1", "conv_x", "user", "年假几天？", None, 4, "2026-06-10T00:00:01"),
        )
        conn.execute(
            """
            INSERT INTO messages
                (id, conversation_id, role, content, sources, token_count, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            ("m2", "conv_x", "assistant", "满一年五天[1]。", None, 7, "2026-06-10T00:00:02"),
        )

    generator = FakeGenerator(["病假规定见制度[1]。"])
    service = ChatService(
        settings,
        embedder=FakeEmbedder(),
        retriever=FakeRetriever(),
        reranker=FakeReranker(),
        generator=generator,
        id_factory=FixedIds(),
    )

    list(service.stream_chat("kb_1", "那病假呢？", conversation_id="conv_x"))

    # 历史按时间正序传入，且不包含当前这条问题（先读历史后落库）
    assert generator.calls[0]["history"] == [
        {"role": "user", "content": "年假几天？"},
        {"role": "assistant", "content": "满一年五天[1]。"},
    ]


def test_chat_service_appends_to_existing_conversation(tmp_path):
    settings = Settings(data_dir=str(tmp_path))
    init_db(settings)
    seed_kb(settings)
    with closing(get_connection(settings)) as conn, conn:
        conn.execute(
            """
            INSERT INTO conversations (id, kb_id, title, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                "conv_existing",
                "kb_1",
                "Existing",
                "2026-06-10T00:00:00",
                "2026-06-10T00:00:00",
            ),
        )
    service = ChatService(
        settings,
        embedder=FakeEmbedder(),
        retriever=FakeRetriever(),
        reranker=FakeReranker(),
        generator=FakeGenerator(["回答[1]"]),
        id_factory=FixedIds(),
    )

    events = list(
        service.stream_chat(
            "kb_1",
            "继续问",
            conversation_id="conv_existing",
        )
    )

    assert events[-1].data["conversation_id"] == "conv_existing"
    conversations = fetch_rows(settings, "conversations")
    assert [row["id"] for row in conversations] == ["conv_existing"]
    messages = fetch_rows(settings, "messages")
    assert [(row["role"], row["content"]) for row in messages] == [
        ("user", "继续问"),
        ("assistant", "回答[1]"),
    ]
