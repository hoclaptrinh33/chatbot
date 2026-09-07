"""Unit tests for semantic-cache eligibility (no FastAPI/Qdrant import)."""
import importlib.util
from pathlib import Path

_mod_path = Path(__file__).resolve().parents[1] / "app" / "services" / "cache_policy.py"
_spec = importlib.util.spec_from_file_location("cache_policy", _mod_path)
_mod = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_mod)
is_cacheable_answer = _mod.is_cacheable_answer


def test_empty_is_not_cacheable():
    assert is_cacheable_answer("") is False
    assert is_cacheable_answer("   ") is False
    assert is_cacheable_answer(None) is False


def test_empty_model_reply_is_not_cacheable():
    assert is_cacheable_answer("Xin lỗi, mô hình AI đã trả về câu trả lời rỗng.") is False


def test_server_and_timeout_errors_are_not_cacheable():
    assert is_cacheable_answer("Lỗi Server AI (Mã lỗi 503): quá tải") is False
    assert is_cacheable_answer("Không thể kết nối đến máy chủ AI tại http://host.docker.internal:8080/v1") is False
    assert is_cacheable_answer("Thời gian yêu cầu sinh câu trả lời từ AI đã hết hạn (Timeout). Vui lòng thử lại sau.") is False


def test_real_answer_is_cacheable():
    assert is_cacheable_answer("AIRC là trung tâm nghiên cứu trí tuệ nhân tạo.") is True
