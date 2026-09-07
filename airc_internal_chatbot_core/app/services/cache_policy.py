"""Rules for what RAG answers may enter the semantic cache."""
from typing import Optional

# Substrings of system/LLM failure replies. Case-insensitive.
UNCACHEABLE_MARKERS = (
    "mô hình AI đã trả về câu trả lời rỗng",
    "không nhận được phản hồi hợp lệ từ mô hình AI",
    "Lỗi Server AI",
    "Không thể kết nối đến máy chủ AI",
    "đã hết hạn (Timeout)",
    "hệ thống gặp lỗi khi kết nối đến AI",
    "hệ thống AI đang gặp sự cố",
)


def is_cacheable_answer(answer: Optional[str]) -> bool:
    """True only for a real model answer, not empty or known error text."""
    if not answer or not str(answer).strip():
        return False
    text = str(answer).casefold()
    return not any(marker.casefold() in text for marker in UNCACHEABLE_MARKERS)
