"""Unit tests for LLM endpoint/key pairing (no FastAPI/Qdrant import)."""
import importlib.util
from pathlib import Path

_mod_path = Path(__file__).resolve().parents[1] / "app" / "services" / "llm_resolve.py"
_spec = importlib.util.spec_from_file_location("llm_resolve", _mod_path)
_mod = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_mod)
mask_api_key = _mod.mask_api_key
normalize_base_url = _mod.normalize_base_url
resolve_llm_connection = _mod.resolve_llm_connection


def test_normalize_strips_chat_completions_suffix():
    assert (
        normalize_base_url("https://api.openai.com/v1/chat/completions/")
        == "https://api.openai.com/v1"
    )


def test_bot_endpoint_does_not_reuse_system_key():
    url, key = resolve_llm_connection(
        bot_base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        bot_api_key=None,
        system_base_url="http://localhost:11434/v1",
        system_api_key="ollama-system-key",
    )
    assert url == "https://generativelanguage.googleapis.com/v1beta/openai"
    assert key is None


def test_bot_endpoint_uses_bot_key_only():
    url, key = resolve_llm_connection(
        bot_base_url="https://api.openai.com/v1",
        bot_api_key="sk-bot",
        system_base_url="http://localhost:11434/v1",
        system_api_key="ollama-system-key",
    )
    assert url == "https://api.openai.com/v1"
    assert key == "sk-bot"


def test_api_key_only_stays_on_system_endpoint():
    url, key = resolve_llm_connection(
        bot_base_url="  ",
        bot_api_key="sk-bot",
        system_base_url="http://localhost:11434/v1",
        system_api_key="ollama-system-key",
    )
    assert url == "http://localhost:11434/v1"
    assert key == "sk-bot"


def test_empty_bot_falls_back_to_system():
    url, key = resolve_llm_connection(
        bot_base_url=None,
        bot_api_key=None,
        system_base_url="http://localhost:11434/v1",
        system_api_key="ollama",
    )
    assert url == "http://localhost:11434/v1"
    assert key == "ollama"


def test_mask_api_key():
    assert mask_api_key("sk-abcdefghij") == "sk-••••ghij"
    assert mask_api_key("short") == "••••••••"
    assert mask_api_key("") is None
