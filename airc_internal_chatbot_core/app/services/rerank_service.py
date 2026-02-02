"""
Reranker Service - Cross-Encoder cho reranking kết quả tìm kiếm
Service này sử dụng mô hình Cross-Encoder để đánh giá lại độ phù hợp (relevance score)
giữa câu hỏi và các đoạn văn bản (chunks) trả về từ Vector Search.
"""
from sentence_transformers import CrossEncoder
from typing import List, Dict, Optional
import logging
import numpy as np

logger = logging.getLogger(__name__)

# Registry các reranker models được hỗ trợ
# Performance benchmarks (trên CPU):
#   - ms-marco-MiniLM-L-6-v2:  ~100-200ms cho 10 chunks (nhẹ nhất)
#   - ms-marco-MiniLM-L-12-v2: ~200-400ms cho 10 chunks (cân bằng)
#   - bge-reranker-v2-m3:      ~2-8s cho 10 chunks (chính xác nhất, đa ngôn ngữ)
RERANKER_MODELS = {
    # Lightweight - Nhanh nhất (English-optimized nhưng works OK với Vietnamese)
    "ms-marco-MiniLM-L-6-v2": "cross-encoder/ms-marco-MiniLM-L-6-v2",
    # Medium - Cân bằng giữa tốc độ và độ chính xác
    "ms-marco-MiniLM-L-12-v2": "cross-encoder/ms-marco-MiniLM-L-12-v2",
    # Heavy - Chính xác nhất, đa ngôn ngữ (tốt cho tiếng Việt)
    "bge-reranker-v2-m3": "BAAI/bge-reranker-v2-m3",
    # Legacy aliases for backward compatibility
    "cross-encoder/ms-marco-MiniLM-L-6-v2": "cross-encoder/ms-marco-MiniLM-L-6-v2",
}

# UI-friendly display names and descriptions
RERANKER_INFO = {
    "ms-marco-MiniLM-L-6-v2": {
        "name": "MiniLM-L6 (Siêu nhanh)",
        "description": "~100-200ms, độ chính xác tốt cho câu hỏi đơn giản",
        "speed": "fast",
        "accuracy": "good"
    },
    "ms-marco-MiniLM-L-12-v2": {
        "name": "MiniLM-L12 (Cân bằng)",
        "description": "~200-400ms, cân bằng giữa tốc độ và độ chính xác",
        "speed": "medium",
        "accuracy": "better"
    },
    "bge-reranker-v2-m3": {
        "name": "BGE-M3 (Chính xác nhất)",
        "description": "~2-8s, tối ưu cho tiếng Việt và câu hỏi phức tạp",
        "speed": "slow",
        "accuracy": "best"
    },
    "None": {
        "name": "Không dùng Reranker",
        "description": "Nhanh nhất, chỉ dùng Vector similarity",
        "speed": "fastest",
        "accuracy": "basic"
    }
}

DEFAULT_RERANKER = "ms-marco-MiniLM-L-6-v2"  # Changed to faster default


class RerankService:
    """Service xử lý reranking kết quả search sử dụng Cross-Encoder"""
    
    def __init__(self):
        self.models: Dict[str, CrossEncoder] = {}
        self._loaded = False
    
    def preload_models(self, model_names: Optional[List[str]] = None):
        """
        Tải trước các model reranker vào bộ nhớ (Preload)
        
        Args:
            model_names: Danh sách tên model cần tải (None = tải model mặc định)
        """
        if self._loaded:
            logger.info("[RERANK] Models đã được tải trước đó")
            return
        
        models_to_load = model_names or [DEFAULT_RERANKER]
        
        logger.info(f"[RERANK] Bắt đầu preload models={models_to_load}")
        
        for model_name in models_to_load:
            if model_name not in RERANKER_MODELS:
                logger.warning(f"[RERANK] Model không xác định: {model_name}, bỏ qua")
                continue
            
            if model_name in self.models:
                logger.info(f"[RERANK] Model {model_name} đã sẵn sàng")
                continue
            
            try:
                model_path = RERANKER_MODELS[model_name]
                logger.info(f"[RERANK] Đang tải model={model_name} path={model_path}")
                
                # Load model với max_length 512 tokens
                self.models[model_name] = CrossEncoder(model_path, max_length=512)
                
                logger.info(f"[RERANK] Tải thành công model={model_name}")
            except Exception as e:
                logger.exception(f"[RERANK] Lỗi tải model={model_name}")
        
        self._loaded = True
        logger.info(f"[RERANK] Hoàn tất preload, tổng số models={len(self.models)}")
    
    def rerank(
        self,
        question: str,
        chunks: List[Dict],
        model_name: str = DEFAULT_RERANKER,
        top_k: int = 5
    ) -> List[Dict]:
        """
        Sắp xếp lại (Rerank) danh sách chunks dựa trên độ liên quan ngữ nghĩa với câu hỏi
        
        Args:
            question: Câu hỏi của người dùng
            chunks: Danh sách chunks cần rerank (mỗi chunk phải có trường 'text')
            model_name: Tên model reranker sử dụng
            top_k: Số lượng chunks muốn lấy sau khi rerank
        
        Returns:
            List chunks đã được sắp xếp giảm dần theo điểm rerank (rerank_score)
        """
        if not chunks:
            return []
        
        # Đảm bảo model đã được load
        if not self._loaded or model_name not in self.models:
            logger.warning(f"[RERANK] Model {model_name} chưa load, đang tiến hành tải...")
            self.preload_models([model_name])
        
        model = self.models.get(model_name)
        if not model:
            logger.error(f"[RERANK] Model {model_name} không khả dụng, trả về thứ tự gốc")
            return chunks[:top_k]
        
        try:
            # Chuẩn bị cặp dữ liệu input: [[câu hỏi, nội dung chunk], ...]
            pairs = [[question, chunk.get('text', '')] for chunk in chunks]
            
            logger.info(f"[RERANK] Đang chấm điểm {len(pairs)} chunks với model {model_name}")
            
            # Dự đoán điểm số tương đồng (relevance score)
            scores = model.predict(pairs)
            
            # Gán điểm rerank_score vào từng chunk
            for i, chunk in enumerate(chunks):
                chunk['rerank_score'] = float(scores[i])
            
            # Sắp xếp giảm dần theo điểm số
            chunks_sorted = sorted(
                chunks,
                key=lambda x: x.get('rerank_score', -999),
                reverse=True
            )
            
            # Log điểm cao nhất để debug
            if chunks_sorted:
                top_score = chunks_sorted[0].get('rerank_score', 0)
                logger.info(f"[RERANK] Điểm cao nhất={top_score:.4f}")
            
            return chunks_sorted[:top_k]
        
        except Exception as e:
            logger.exception("[RERANK] Lỗi trong quá trình rerank, trả về thứ tự gốc")
            return chunks[:top_k]


# Singleton instance
rerank_service = RerankService()
