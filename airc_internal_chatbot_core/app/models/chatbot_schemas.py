
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, field_validator
from app.core.config import settings

class ChatbotConfigModel(BaseModel):
    """
    Cấu hình đầy đủ cho Chatbot RAG Pipeline
    Pipeline: Query → Embedding → Retrieval → Reranking → Generation
    """
    
    # ═══════════════════════════════════════════════════════════════
    # 📊 EMBEDDING SETTINGS - Cấu hình vector hóa câu hỏi
    # ═══════════════════════════════════════════════════════════════
    embedding_model: str = Field(
        default="vietnamese-sbert", 
        description="Model embedding: vietnamese-sbert, multilingual-e5, openai-ada"
    )
    
    # ═══════════════════════════════════════════════════════════════
    # 🔍 RETRIEVAL SETTINGS - Cấu hình tìm kiếm trong Vector DB
    # ═══════════════════════════════════════════════════════════════
    search_mode: str = Field(
        default="hybrid", 
        pattern="^(hybrid|vector|keyword)$", 
        description="Chiến lược tìm kiếm: hybrid (vector+keyword), vector (semantic only), keyword (BM25)"
    )
    top_k: int = Field(default=5, ge=1, le=20, description="Số chunks lấy từ vector DB")
    similarity_threshold: float = Field(default=0.25, ge=0.0, le=1.0, description="Ngưỡng điểm tương đồng tối thiểu (0-1). vietnamese-sbert thường ~0.25–0.40 với câu đúng chủ đề.")
    
    # ═══════════════════════════════════════════════════════════════
    # 📈 RERANKING SETTINGS - Sắp xếp lại kết quả tìm kiếm
    # ═══════════════════════════════════════════════════════════════
    reranker: Optional[str] = Field(
        default="ms-marco-MiniLM-L-6-v2", 
        description="""Model reranking để sắp xếp lại kết quả tìm kiếm:
        - None: Không rerank (nhanh nhất)
        - ms-marco-MiniLM-L-6-v2: Siêu nhanh (~100-200ms)
        - ms-marco-MiniLM-L-12-v2: Cân bằng (~200-400ms)
        - bge-reranker-v2-m3: Chính xác nhất (~2-8s, tốt cho tiếng Việt)
        - Semantic/CrossEncoder: Legacy aliases"""
    )
    rerank_top_n: Optional[int] = Field(
        default=None, 
        ge=1, le=10, 
        description="Số kết quả giữ lại sau rerank (None=giữ tất cả top_k)"
    )
    
    # ═══════════════════════════════════════════════════════════════
    # 🤖 LLM GENERATION SETTINGS - Cấu hình sinh câu trả lời
    # ═══════════════════════════════════════════════════════════════
    model: Optional[str] = Field(
        default=settings.llm_model_name, 
        description="Model LLM sử dụng"
    )
    api_base_url: Optional[str] = Field(
        None,
        max_length=500,
        description="OpenAI-compatible endpoint riêng. Trống = dùng endpoint hệ thống. Phải đi kèm API key của cùng nhà cung cấp.",
    )
    api_key: Optional[str] = Field(
        None, 
        description="API Key riêng. Nếu không nhập endpoint thì key gửi tới endpoint hệ thống (chỉ đúng nhà cung cấp)."
    )
    temperature: Optional[float] = Field(
        default=0.7, ge=0.0, le=2.0, 
        description="Độ sáng tạo: 0=deterministic, 0.7=balanced, 2=creative"
    )
    max_tokens: Optional[int] = Field(
        default=2048, gt=0, le=8192, 
        description="Số token tối đa trong response"
    )
    
    # ═══════════════════════════════════════════════════════════════
    # 📝 PROMPT SETTINGS - System prompt cho LLM
    # ═══════════════════════════════════════════════════════════════
    system_prompt: Optional[str] = Field(
        None, 
        description="Prompt hệ thống tùy chỉnh (override default RAG prompt)"
    )
    
    # ═══════════════════════════════════════════════════════════════
    # ⚠️ NO CONTEXT BEHAVIOR - Hành vi khi không tìm thấy tài liệu
    # ═══════════════════════════════════════════════════════════════
    no_context_behavior: str = Field(
        default="reject", 
        pattern="^(reject|fallback_llm|custom_message)$",
        description="reject=từ chối, fallback_llm=dùng LLM, custom_message=thông báo tùy chỉnh"
    )
    no_context_message: Optional[str] = Field(
        default=None,
        description="Thông báo khi không tìm thấy (dùng với custom_message)"
    )
    
    # ═══════════════════════════════════════════════════════════════
    # 📝 CONTEXT & HISTORY SETTINGS - Quản lý ngữ cảnh và lịch sử
    # ═══════════════════════════════════════════════════════════════
    enable_query_reformulation: bool = Field(
        default=False,
        description="Bật trên bot chính xác. Tắt mặc định (bot nhanh) vì thêm 1 lần gọi LLM."
    )
    enable_history_compression: bool = Field(
        default=False,
        description="Bật trên bot chính xác / session dài. Tắt mặc định để giảm latency."
    )
    history_limit: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Số lượt chat thô gần nhất giữ lại"
    )
    buffer_limit: int = Field(
        default=2,
        ge=1,
        le=5,
        description="Số lượt chat đệm trước khi kích hoạt nén"
    )
    compression_model: str = Field(
        default="gemini-1.5-flash",
        description="Model LLM dùng để viết lại câu hỏi và tóm tắt lịch sử"
    )

    @field_validator("api_base_url", "api_key", mode="before")
    @classmethod
    def empty_str_to_none(cls, value):
        if isinstance(value, str) and not value.strip():
            return None
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("api_base_url")
    @classmethod
    def validate_api_base_url(cls, value):
        if value and not value.startswith(("http://", "https://")):
            raise ValueError("LLM endpoint phải bắt đầu bằng http:// hoặc https://")
        return value


class ChatbotCreate(BaseModel):
    """Request: Tạo chatbot mới (ADMIN ONLY)"""
    name: str = Field(..., min_length=3, max_length=100, description="Tên chatbot")
    description: Optional[str] = Field(None, max_length=500)
    icon: Optional[str] = None
    
    # Configuration
    config: Optional[ChatbotConfigModel] = Field(default_factory=ChatbotConfigModel)
    
    # Knowledge linking
    dataset_ids: List[str] = Field(default_factory=list, description="Datasets linked to this chatbot")
    
    # RBAC - Chỉ theo role, không theo user cụ thể
    allowed_roles: List[str] = Field(default=["student", "teacher", "admin"], description="Roles allowed to use this chatbot")
    visibility: str = Field(default="public", description="public, private")


class ChatbotUpdate(BaseModel):
    """Request: Cập nhật chatbot"""
    name: Optional[str] = Field(None, min_length=3, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    icon: Optional[str] = None
    config: Optional[ChatbotConfigModel] = None
    dataset_ids: Optional[List[str]] = None
    allowed_roles: Optional[List[str]] = None
    visibility: Optional[str] = None
    is_active: Optional[bool] = None


class ChatbotResponse(BaseModel):
    """Response: Chatbot info"""
    id: str
    name: str
    description: Optional[str] = None
    icon: Optional[str] = None
    config: ChatbotConfigModel
    dataset_ids: List[str]
    allowed_roles: List[str]
    visibility: str
    owner_id: str
    is_active: bool = True
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ChatbotAssignDatasetsRequest(BaseModel):
    """Request: Gán datasets cho chatbot"""
    dataset_ids: List[str] = Field(..., min_length=1, description="List of dataset IDs to assign")
