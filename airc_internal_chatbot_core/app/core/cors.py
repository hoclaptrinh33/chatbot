"""CORS helpers — never pair wildcard origin with credentials."""
import os
from typing import List


DEFAULT_PROD_ORIGINS = [
    "https://ragairc.neovort.shop",
]


def resolve_cors_origins() -> List[str]:
    raw = os.getenv("ALLOWED_ORIGINS", "").strip()
    environment = os.getenv("ENVIRONMENT", "development").lower()
    if raw:
        origins = [item.strip() for item in raw.split(",") if item.strip() and item.strip() != "*"]
        if origins:
            return origins
    if environment == "production":
        return list(DEFAULT_PROD_ORIGINS)
    return [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
