"""
Embedding Service - Xử lý text embedding với sentence transformers
"""
import os
import logging
from sentence_transformers import SentenceTransformer
from typing import Optional, List
import numpy as np

logger = logging.getLogger(__name__)

# Cấu hình models registry
# Vietnamese-optimized embedding model
MODEL_REGISTRY = {
    "keepitreal/vietnamese-sbert": "keepitreal/vietnamese-sbert",
    # Backup: Multilingual option
    # "intfloat/multilingual-e5-small": "intfloat/multilingual-e5-small",
}

DEFAULT_MODEL = "keepitreal/vietnamese-sbert"

# Cache embedders
_EMBEDDERS: dict[str, SentenceTransformer] = {}

# Giới hạn threads cho performance
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")


class EmbeddingService:
    """Service xử lý embedding"""
    
    def __init__(self):
        self.embedders = _EMBEDDERS
    
    def preload_models(self) -> None:
        """Preload các models vào memory khi startup"""
        if not MODEL_REGISTRY:
            logger.warning("[EMBED] No models configured for preload")
            return
        
        logger.info("[EMBED] Preload start models=%s", list(MODEL_REGISTRY.keys()))
        
        for model_name, path in MODEL_REGISTRY.items():
            if model_name in self.embedders:
                continue
            
            logger.info("[EMBED] Loading model=%s path=%s", model_name, path)
            self.embedders[model_name] = SentenceTransformer(path)
            logger.info("[EMBED] Model loaded=%s", model_name)
        
        logger.info("[EMBED] Preload done total=%d", len(self.embedders))
    
    def _resolve_model(self, model_name: Optional[str]) -> str:
        """Resolve model name, fallback nếu không tìm thấy"""
        if model_name and model_name in MODEL_REGISTRY:
             return model_name
        
        if model_name:
            logger.warning(
                "[EMBED] Unknown model=%s → fallback=%s",
                model_name,
                DEFAULT_MODEL,
            )
        
        return DEFAULT_MODEL
    
    def _load_model(self, model_name: str) -> None:
        """Load specific model if not already loaded"""
        if model_name in self.embedders:
            return

        if model_name not in MODEL_REGISTRY:
            raise ValueError(f"Model {model_name} not found in registry")

        path = MODEL_REGISTRY[model_name]
        logger.info("[EMBED] Lazy loading model=%s path=%s", model_name, path)
        try:
            self.embedders[model_name] = SentenceTransformer(path)
            logger.info("[EMBED] Model loaded=%s", model_name)
        except Exception as e:
            logger.error("[EMBED] Failed to load model=%s: %s", model_name, e)
            raise RuntimeError(f"Failed to load embedding model: {e}")

    def embed_texts(
        self, 
        texts: List[str], 
        model_name: Optional[str] = None,
        batch_size: int = 16
    ) -> np.ndarray:
        """
        Embed texts thành vectors
        """
        if not texts:
            return np.array([])
        
        resolved_model = self._resolve_model(model_name)
        
        # Lazy load model
        self._load_model(resolved_model)
        
        embedder = self.embedders[resolved_model]
        
        total = len(texts)
        vectors = []
        
        logger.info("[EMBED] Start total=%d model=%s", total, resolved_model)
        
        for i in range(0, total, batch_size):
            batch = texts[i:i + batch_size]
            vecs = embedder.encode(batch, normalize_embeddings=True)
            vectors.extend(vecs)
            
            logger.info(
                "[EMBED][PROGRESS] %d/%d (%.1f%%)",
                min(i + batch_size, total),
                total,
                min(i + batch_size, total) * 100.0 / total,
            )
        
        result = np.array(vectors, dtype=np.float32)
        logger.info("[EMBED] Done vectors=%d", len(result))
        return result


# Singleton instance
embedding_service = EmbeddingService()
