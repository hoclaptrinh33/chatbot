"""Catalog of Edge-TTS voices allowed for live mode."""

DEFAULT_TTS_VOICE = "vi-VN-HoaiMyNeural"

TTS_VOICE_CATALOG = [
    {
        "id": "vi-VN-HoaiMyNeural",
        "label": "Hoài My (nữ)",
        "locale": "vi-VN",
    },
    {
        "id": "vi-VN-NamMinhNeural",
        "label": "Nam Minh (nam)",
        "locale": "vi-VN",
    },
]

ALLOWED_TTS_VOICES = {item["id"] for item in TTS_VOICE_CATALOG}


def normalize_tts_voice(voice: str | None) -> str:
    if voice and voice in ALLOWED_TTS_VOICES:
        return voice
    return DEFAULT_TTS_VOICE
