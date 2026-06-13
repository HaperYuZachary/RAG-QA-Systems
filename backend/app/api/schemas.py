from pydantic import BaseModel, Field, field_validator


DEFAULT_DEBUG_TOP_K = 10
MAX_DEBUG_TOP_K = 50


class ChatRequest(BaseModel):
    kb_id: str
    question: str
    conversation_id: str | None = None

    @field_validator("kb_id", "question", "conversation_id")
    @classmethod
    def strip_required_text(cls, value: str | None) -> str | None:
        if value is None:
            return None

        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be blank")
        return stripped


class DebugSearchRequest(BaseModel):
    kb_id: str
    query: str
    top_k: int = Field(default=DEFAULT_DEBUG_TOP_K, ge=1, le=MAX_DEBUG_TOP_K)

    @field_validator("top_k", mode="before")
    @classmethod
    def default_top_k_when_null(cls, value):
        return DEFAULT_DEBUG_TOP_K if value is None else value

    @field_validator("kb_id", "query")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be blank")
        return stripped


class DebugTiming(BaseModel):
    embedding_ms: float
    retrieval_ms: float
    rerank_ms: float
    total_ms: float


class DebugSearchHit(BaseModel):
    id: str
    text: str
    metadata: dict = Field(default_factory=dict)
    vector_rank: int | None = None
    vector_distance: float | None = None
    bm25_rank: int | None = None
    bm25_score: float | None = None
    rrf_score: float
    rerank_score: float | None = None


class DebugSearchResponse(BaseModel):
    query: str
    hits: list[DebugSearchHit]
    timings: DebugTiming


class KnowledgeBaseCreateRequest(BaseModel):
    name: str
    description: str = ""

    @field_validator("description", mode="before")
    @classmethod
    def default_description_when_null(cls, value):
        return "" if value is None else value

    @field_validator("name")
    @classmethod
    def strip_required_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be blank")
        return stripped

    @field_validator("description")
    @classmethod
    def strip_description(cls, value: str) -> str:
        return value.strip()


class KnowledgeBaseUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None

    @field_validator("name")
    @classmethod
    def strip_optional_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be blank")
        return stripped

    @field_validator("description")
    @classmethod
    def strip_optional_description(cls, value: str | None) -> str | None:
        return value if value is None else value.strip()


class KnowledgeBaseResponse(BaseModel):
    id: str
    name: str
    description: str
    created_at: str
    updated_at: str
    document_count: int


class DocumentResponse(BaseModel):
    id: str
    kb_id: str
    filename: str
    file_type: str
    file_size: int
    chunk_count: int
    status: str
    error_msg: str | None = None
    created_at: str


class DocumentStatusResponse(BaseModel):
    id: str
    status: str
    chunk_count: int
    error_msg: str | None = None


class UploadResultItem(BaseModel):
    document_id: str
    filename: str
    status: str
    chunk_count: int
    duplicate: bool = False
    error_msg: str | None = None


class UploadResponse(BaseModel):
    documents: list[UploadResultItem]
