"""
Semantic Cache Service - Cache câu hỏi thường gặp
Sử dụng embedding similarity để cache và retrieve câu trả lời
"""
from typing import Optional, Dict, List
import logging
import numpy as np
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class SemanticCacheService:
    """
    Service cache semantically
    Sử dụng in-memory cache với embedding similarity
    """
    
    def __init__(
        self,
        similarity_threshold: float = 0.90,
        max_cache_size: int = 100,
        ttl_seconds: int = 3600
    ):
        """
        Initialize semantic cache
        
        Args:
            similarity_threshold: Ngưỡng similarity để coi là cache hit (0.90 = 90%)
            max_cache_size: Số lượng entries tối đa trong cache
            ttl_seconds: Time-to-live cho mỗi cache entry (seconds)
        """
        self.cache: List[Dict] = []  # List of {question, embedding, answer, timestamp}
        self.similarity_threshold = similarity_threshold
        self.max_cache_size = max_cache_size
        self.ttl_seconds = ttl_seconds
        
        self._hits = 0
        self._misses = 0
    
    def get(
        self,
        question: str,
        question_embedding: np.ndarray,
        suffix: str = ""
    ) -> Optional[str]:
        """
        Tìm kiếm câu trả lời trong cache
        
        Args:
            question: Câu hỏi
            question_embedding: Embedding vector của câu hỏi
            suffix: Optional suffix to isolate cache (e.g., "_bot_123")
        
        Returns:
            Cached answer nếu tìm thấy, None nếu miss
        """
        if not self.cache:
            self._misses += 1
            return None
        
        # Clean expired entries
        self._clean_expired()
        
        # Normalize input embedding
        q_vec_norm = question_embedding / np.linalg.norm(question_embedding)
        
        best_similarity = -1
        best_entry = None
        
        for entry in self.cache:
            # Filter by suffix (chatbot isolation)
            if entry.get('suffix', '') != suffix:
                continue
                
            cached_vec = np.array(entry['embedding'])
            cached_vec_norm = cached_vec / np.linalg.norm(cached_vec)
            
            # Cosine similarity
            similarity = np.dot(q_vec_norm, cached_vec_norm)
            
            if similarity > best_similarity:
                best_similarity = similarity
                best_entry = entry
        
        # Check if similarity exceeds threshold
        if best_similarity >= self.similarity_threshold:
            self._hits += 1
            logger.info(
                f"[CACHE] HIT similarity={best_similarity:.4f} suffix={suffix} "
                f"question_preview={question[:50]}..."
            )
            return best_entry['answer']
        else:
            self._misses += 1
            logger.debug(
                f"[CACHE] MISS best_similarity={best_similarity:.4f} "
                f"threshold={self.similarity_threshold} suffix={suffix}"
            )
            return None
    
    def set(
        self,
        question: str,
        question_embedding: np.ndarray,
        answer: str,
        suffix: str = ""
    ):
        """
        Lưu câu hỏi-trả lời vào cache
        
        Args:
            question: Câu hỏi
            question_embedding: Embedding vector
            answer: Câu trả lời cần cache
            suffix: Optional suffix to isolate cache (e.g., "_bot_123")
        """
        # Check cache size limit
        if len(self.cache) >= self.max_cache_size:
            # Remove oldest entry
            self.cache.pop(0)
            logger.debug(f"[CACHE] Evicted oldest entry, size={len(self.cache)}")
        
        # Add new entry
        entry = {
            'question': question,
            'embedding': question_embedding.tolist(),
            'answer': answer,
            'timestamp': datetime.utcnow(),
            'suffix': suffix  # NEW: Chatbot isolation
        }
        
        self.cache.append(entry)
        
        logger.info(
            f"[CACHE] SET cache_size={len(self.cache)} suffix={suffix} "
            f"question_preview={question[:50]}..."
        )
    
    def _clean_expired(self):
        """Xóa các entries đã hết hạn"""
        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=self.ttl_seconds)
        
        original_size = len(self.cache)
        self.cache = [
            entry for entry in self.cache
            if entry['timestamp'] > cutoff
        ]
        
        removed = original_size - len(self.cache)
        if removed > 0:
            logger.info(f"[CACHE] Cleaned {removed} expired entries")
    
    def clear(self):
        """Xóa toàn bộ cache"""
        self.cache.clear()
        self._hits = 0
        self._misses = 0
        logger.info("[CACHE] Cleared all entries")
    
    def get_stats(self) -> Dict:
        """Lấy thống kê cache performance"""
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0
        
        return {
            'cache_size': len(self.cache),
            'hits': self._hits,
            'misses': self._misses,
            'hit_rate': round(hit_rate, 2)
        }


# Singleton instance
semantic_cache_service = SemanticCacheService(
    similarity_threshold=0.90,  # 90% similarity for Vietnamese
    max_cache_size=100,
    ttl_seconds=3600  # 1 hour
)
