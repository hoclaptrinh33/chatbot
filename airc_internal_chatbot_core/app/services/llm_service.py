"""
LLM Service - Tích hợp LLM (OpenAI-compatible)
Service này chịu trách nhiệm gọi API của LLM (Local hoặc Cloud) để sinh câu trả lời
"""
import os
import logging
import httpx
from typing import Optional, AsyncGenerator, Dict, Any
import json
from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMService:
    """
    Service quản lý việc gọi API LLM thông qua chuẩn OpenAI-compatible.
    Hỗ trợ kết nối linh hoạt tới cả mô hình local (Ollama, vLLM...) và mô hình cloud (OpenAI, DeepSeek, Groq...).
    Áp dụng Singleton pattern.
    """
    
    def __init__(self):
        # Khởi tạo client httpx không đồng bộ dùng chung để tối ưu hiệu năng kết nối (connection pooling)
        # Thiết lập timeout mặc định là 60 giây vì các mô hình có thể cần thời gian suy luận lâu hơn
        self.client = httpx.AsyncClient(timeout=60.0)

    def _configure(self) -> None:
        """Startup hook — client is ready; nothing extra to load."""
        return
    
    async def _resolved_connection(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        """Pair endpoint + key: bot override, else runtime system settings, else .env."""
        from app.services.llm_resolve import resolve_llm_connection
        from app.services.system_settings_service import get_effective_llm_settings

        try:
            system = await get_effective_llm_settings()
            sys_url = system["base_url"]
            sys_key = system.get("api_key")
            sys_model = system.get("model_name") or settings.llm_model_name
        except Exception as e:
            logger.warning("[LLM] Falling back to env settings: %s", e)
            sys_url = settings.llm_api_base_url
            sys_key = settings.llm_api_key
            sys_model = settings.llm_model_name

        url, token = resolve_llm_connection(
            bot_base_url=base_url,
            bot_api_key=api_key,
            system_base_url=sys_url,
            system_api_key=sys_key,
        )
        return url, token, sys_model

    async def generate(
        self, 
        prompt: str, 
        api_key: Optional[str] = None, 
        model_name: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        *,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> str:
        """
        Sinh văn bản từ prompt sử dụng mô hình qua OpenAI-compatible API.
        
        Args:
            prompt: Chuỗi prompt đầu vào đã được build đầy đủ context
            api_key: Optional API Key override (per-chatbot)
            model_name: Optional custom model name (e.g., qwen2.5:7b hoặc gpt-4o)
            temperature: Độ sáng tạo của câu trả lời (0.0 đến 2.0)
            max_tokens: Số token tối đa trả về
            base_url: Optional OpenAI-compatible endpoint override (per-chatbot)
            timeout: Optional per-request timeout in seconds (auxiliary LLM hops)
        
        Returns:
            str: Nội dung câu trả lời từ AI
        """
        resolved_url, token, default_model = await self._resolved_connection(api_key, base_url)
        target_model = model_name or default_model
        
        # Chuẩn hóa URL, đảm bảo kết nối đến endpoint chat completions
        endpoint = f"{resolved_url}/chat/completions"
        
        # Thiết lập headers
        headers = {
            "Content-Type": "application/json"
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
            
        # Xây dựng payload theo chuẩn OpenAI Chat Completion
        payload = {
            "model": target_model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        try:
            logger.info(f"[LLM] Calling LLM API - Endpoint: {endpoint} | Model: {target_model}")
            
            response = await self.client.post(
                endpoint, json=payload, headers=headers, timeout=timeout
            )
            
            # Kiểm tra HTTP status code
            if response.status_code != 200:
                logger.error(f"[LLM] API returned error status: {response.status_code} | Detail: {response.text}")
                try:
                    err_json = response.json()
                    err_detail = err_json.get("error", {})
                    if isinstance(err_detail, dict):
                        err_msg = err_detail.get("message") or err_detail.get("details")
                    else:
                        err_msg = str(err_detail)
                except Exception:
                    err_msg = None
                
                friendly_message = f"Lỗi Server AI (Mã lỗi {response.status_code}): "
                if err_msg:
                    # Phân tích thông báo lỗi quá tải, giới hạn
                    if response.status_code == 503 or "demand" in err_msg.lower() or "overloaded" in err_msg.lower():
                        friendly_message += "Mô hình hiện đang quá tải do có lượng truy cập rất cao. Vui lòng thử lại sau vài giây hoặc cấu hình đổi sang mô hình khác."
                    elif response.status_code == 429:
                        friendly_message += "Đã vượt quá giới hạn số lượt gọi (Rate Limit) cho phép của API Key. Vui lòng kiểm tra lại hạn mức tài khoản."
                    elif response.status_code == 401 or response.status_code == 403:
                        friendly_message += "Khóa API Key không hợp lệ hoặc đã hết hạn. Vui lòng cập nhật cấu hình API."
                    else:
                        friendly_message += f"{err_msg}"
                else:
                    friendly_message += "Phản hồi lỗi từ máy chủ AI không xác định. Vui lòng kiểm tra lại cài đặt dịch vụ."
                return friendly_message
                
            response_json = response.json()
            
            # Parse phản hồi theo chuẩn OpenAI
            choices = response_json.get("choices", [])
            if not choices:
                logger.warning("[LLM] Phản hồi từ server AI không có choices")
                return "Xin lỗi, không nhận được phản hồi hợp lệ từ mô hình AI."
                
            answer = choices[0].get("message", {}).get("content", "")
            if not answer:
                logger.warning("[LLM] Phản hồi từ server AI rỗng")
                return "Xin lỗi, mô hình AI đã trả về câu trả lời rỗng."
                
            logger.info(f"[LLM] LLM responded successfully")
            return answer.strip()
            
        except httpx.ConnectError as conn_err:
            logger.error(f"[LLM] Connection Error: {str(conn_err)}")
            return f"Không thể kết nối đến máy chủ AI tại {resolved_url}. Vui lòng kiểm tra địa chỉ IP và dịch vụ AI."
            
        except httpx.TimeoutException as timeout_err:
            logger.error(f"[LLM] Request Timeout: {str(timeout_err)}")
            return "Thời gian yêu cầu sinh câu trả lời từ AI đã hết hạn (Timeout). Vui lòng thử lại sau."
            
        except Exception as e:
            logger.error(f"[LLM] Lỗi sinh nội dung: {str(e)}")
            return f"Xin lỗi, hệ thống gặp lỗi khi kết nối đến AI: {str(e)[:100]}. Vui lòng liên hệ Admin."

    async def generate_stream(
        self,
        prompt: str,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        *,
        base_url: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Stream tokens from an OpenAI-compatible chat completions endpoint.
        Yields content deltas only. Falls back to a single full-text yield if
        the provider does not support streaming.
        """
        resolved_url, token, default_model = await self._resolved_connection(api_key, base_url)
        target_model = model_name or default_model
        endpoint = f"{resolved_url}/chat/completions"
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        payload: Dict[str, Any] = {
            "model": target_model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }

        try:
            async with self.client.stream("POST", endpoint, json=payload, headers=headers, timeout=120.0) as response:
                if response.status_code != 200:
                    # Non-streaming fallback so the user still gets an answer
                    body = await response.aread()
                    logger.error(f"[LLM] Stream API error {response.status_code}: {body[:400]!r}")
                    fallback = await self.generate(
                        prompt, api_key, model_name, temperature, max_tokens, base_url=base_url
                    )
                    if fallback:
                        yield fallback
                    return

                async for line in response.aiter_lines():
                    if not line:
                        continue
                    if line.startswith("data:"):
                        data = line[5:].strip()
                    else:
                        data = line.strip()
                    if not data or data == "[DONE]":
                        if data == "[DONE]":
                            break
                        continue
                    try:
                        chunk = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    choices = chunk.get("choices") or []
                    if not choices:
                        continue
                    delta = choices[0].get("delta") or {}
                    content = delta.get("content")
                    if not content:
                        # Some providers put text on message.content even in stream
                        content = (choices[0].get("message") or {}).get("content")
                    if content:
                        yield content
        except httpx.ConnectError as conn_err:
            logger.error(f"[LLM] Stream connection error: {conn_err}")
            yield f"Không thể kết nối đến máy chủ AI tại {resolved_url}. Vui lòng kiểm tra địa chỉ IP và dịch vụ AI."
        except httpx.TimeoutException:
            logger.error("[LLM] Stream timeout")
            yield "Thời gian yêu cầu sinh câu trả lời từ AI đã hết hạn (Timeout). Vui lòng thử lại sau."
        except Exception as e:
            logger.error(f"[LLM] Stream error: {e}")
            yield f"Xin lỗi, hệ thống gặp lỗi khi kết nối đến AI: {str(e)[:100]}. Vui lòng liên hệ Admin."


# Singleton instance toàn cục
llm_service = LLMService()
