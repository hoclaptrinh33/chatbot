"""
Pure helpers for pairing LLM endpoint + API key.

A key only works with the provider that issued it. Mixing a Gemini key
with the system Ollama endpoint (or the reverse) fails at call time.
"""
from typing import Optional, Tuple


def normalize_base_url(url: str) -> str:
    """Strip whitespace, trailing slash, and accidental path suffixes."""
    u = (url or "").strip().rstrip("/")
    for suffix in ("/chat/completions", "/models"):
        if u.lower().endswith(suffix):
            u = u[: -len(suffix)].rstrip("/")
    return u


def empty_to_none(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def resolve_llm_connection(
    *,
    bot_base_url: Optional[str],
    bot_api_key: Optional[str],
    system_base_url: str,
    system_api_key: Optional[str],
) -> Tuple[str, Optional[str]]:
    """
    Resolve (base_url, api_key) for one LLM call.

    - Bot endpoint set → that provider. Use the bot key only (do not send
      the system key to a foreign host). Local providers may omit a key.
    - Bot endpoint empty → system endpoint. Bot key overrides system key
      (same provider, different credential).
    """
    bot_url = empty_to_none(bot_base_url)
    bot_key = empty_to_none(bot_api_key)
    sys_url = normalize_base_url(system_base_url)
    sys_key = empty_to_none(system_api_key)

    if bot_url:
        return normalize_base_url(bot_url), bot_key
    return sys_url, bot_key or sys_key


def mask_api_key(api_key: Optional[str]) -> Optional[str]:
    key = empty_to_none(api_key)
    if not key:
        return None
    if len(key) <= 8:
        return "••••••••"
    return f"{key[:3]}••••{key[-4:]}"
