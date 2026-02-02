"""
LLM Service - Tích hợp Google Gemini
Service này chịu trách nhiệm gọi API của Gemini để sinh câu trả lời
"""
import os
import logging
import google.generativeai as genai
from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMService:
    """
    Service quản lý việc gọi Gemini API
    Áp dụng Singleton pattern để chỉ config API key một lần
    """
    
    def __init__(self):
        self._configured = False
    
    def _configure(self):
        """
        Cấu hình Gemini API với Key từ biến môi trường
        Chỉ thực hiện một lần (Lazy initialization)
        """
        if self._configured:
            return
        
        api_key = settings.gemini_api_key
        if not api_key:
            logger.warning("Thiếu GEMINI_API_KEY - Các tính năng AI sẽ bị vô hiệu hóa")
            return
        
        genai.configure(api_key=api_key)
        self._configured = True
    
    async def generate(self, prompt: str, api_key: str = None, model_name: str = None) -> str:
        """
        Sinh văn bản từ prompt sử dụng mô hình Gemini
        
        Args:
            prompt: Chuỗi prompt đầu vào đã được build đầy đủ context
            api_key: Optional API Key override (per-chatbot)
            model_name: Optional custom model name (e.g., gemini-1.5-pro)
        
        Returns:
            str: Nội dung câu trả lời từ AI
            
        Raises:
            RuntimeError: Nếu chưa cấu hình API key
        """
        # Dynamic Configuration
        if api_key:
            # Per-request configuration (Warning: not thread-safe for highly concurrent global usage, but acceptable for this scope)
            genai.configure(api_key=api_key)
        else:
            # System default configuration
            self._configure()
            if not self._configured:
                raise RuntimeError("Gemini API chưa được cấu hình - Thiếu API Key")
        
        # Use provided model or fallback to system default
        target_model = model_name or settings.gemini_model
        
        try:
            # Khởi tạo model (Gemini Pro/Flash implementation)
            model = genai.GenerativeModel(target_model)
            
            # Gọi API sinh nội dung với timeout 30s
            logger.info(f"[LLM] Calling Gemini API - Model: {target_model}")
            response = model.generate_content(
                prompt,
                request_options={"timeout": 30}  # Timeout 30 giây
            )
            logger.info(f"[LLM] Gemini API responded successfully")
            
            # Kiểm tra phản hồi rỗng (Safety filters có thể chặn response)
            if not response or not response.text:
                logger.warning("[LLM] Phản hồi từ Gemini rỗng (Có thể do Safety Filter)")
                return "Xin lỗi, câu hỏi của bạn có thể vi phạm chính sách nội dung của AI, hoặc hệ thống gặp sự cố."
            
            return response.text.strip()
        
        except Exception as e:
            logger.error(f"[LLM] Lỗi sinh nội dung: {str(e)}")
            
            # Chuyển lỗi sang chuỗi thường để check keyword
            err_str = str(e).lower()
            
            # Xử lý lỗi Model Not Found (thường do Model Pro không khả dụng với key free)
            if "404" in err_str and "not found" in err_str:
                logger.warning(f"[LLM] Model {target_model} not found. Fallback to models/gemini-2.5-flash")
                try:
                    fallback_model = genai.GenerativeModel("models/gemini-2.5-flash")
                    response = fallback_model.generate_content(
                        prompt,
                        request_options={"timeout": 30}
                    )
                    if response and response.text:
                        return response.text.strip()
                except Exception as flash_err:
                    logger.warning(f"[LLM] Flash fallback failed: {flash_err}. Trying models/gemini-2.0-flash")
                    try:
                         # Last resort: Gemini 2.0 Flash (stable version)
                        fallback_legacy = genai.GenerativeModel("models/gemini-2.0-flash")
                        response = fallback_legacy.generate_content(
                            prompt,
                            request_options={"timeout": 30}
                        )
                        if response and response.text:
                            return response.text.strip()
                    except Exception as legacy_err:
                        logger.error(f"[LLM] All fallbacks failed. Flash: {flash_err}, Legacy: {legacy_err}")
                        return f"Lỗi Model: Không thể truy cập model Gemini. Kiểm tra API Key/Region. (Chi tiết: {str(flash_err)})"

            # Xử lý các lỗi Quota/Limit/Timeout thường gặp
            if (
                "quota" in err_str or 
                "429" in err_str or 
                "403" in err_str or 
                "resource exhausted" in err_str or
                "permission denied" in err_str or
                "timeout" in err_str or
                "timed out" in err_str
            ):
                logger.warning(f"[LLM] Quota/Timeout/API Error: {err_str}")
                return f"Xin lỗi, hiện tại hệ thống AI đang quá tải hoặc phản hồi quá chậm (Google API Error: {err_str[:50]}...). Vui lòng thử lại sau giây lát."
            
            # Fallback an toàn cho các lỗi khác
            return f"Xin lỗi, tôi đã gặp lỗi kỹ thuật: {err_str}. Vui lòng liên hệ Admin."


# Singleton instance toàn cục
llm_service = LLMService()
