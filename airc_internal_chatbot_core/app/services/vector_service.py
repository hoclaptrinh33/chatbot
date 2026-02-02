"""
Vector Service - Quản lý Qdrant Vector Database
Service này xử lý việc lưu trữ, tìm kiếm và quản lý vector embeddings
"""
from qdrant_client import QdrantClient
from qdrant_client.http import models as rest
from qdrant_client.http.models import Distance, VectorParams, PointStruct
from app.core.config import settings
import numpy as np
import logging
from typing import List, Dict, Optional, Tuple, Any
import uuid

logger = logging.getLogger(__name__)


class VectorService:
    """
    Service kết nối và quản lý Qdrant Vector DB
    Chịu trách nhiệm tạo index, upsert vector và search similarity
    """
    
    def __init__(self):
        self._client = None

    @property
    def client(self):
        if self._client is None:
            logger.info(f"[VECTOR] Initializing Qdrant client at {settings.qdrant_url}")
            self._client = QdrantClient(url=settings.qdrant_url)
        return self._client

    def _get_collection_name(self, dataset_id: str) -> str:
        """Helper format tên collection theo dataset ID"""
        return f"dataset_{dataset_id}"

    def _ensure_collection(self, collection_name: str, vector_size: int):
        """
        Kiểm tra và tạo collection (index) nếu chưa tồn tại
        
        Args:
            collection_name: Tên collection trong Qdrant
            vector_size: Kích thước chiều vector (dimension)
        """
        collections = self.client.get_collections().collections
        exists = any(c.name == collection_name for c in collections)
        
        if not exists:
            logger.info(f"[VECTOR] Khởi tạo collection {collection_name} với size={vector_size}")
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE)
            )

    def add_vectors(
        self, 
        dataset_id: str, 
        vectors: np.ndarray, 
        payloads: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Thêm mới hoặc cập nhật vectors vào Qdrant (Upsert)
        
        Args:
            dataset_id: ID của bộ dữ liệu (dùng làm tên collection)
            vectors: Ma trận vectors numpy array
            payloads: List metadata tương ứng với từng vector
            
        Returns:
            List[str]: Danh sách UUID của các point đã thêm
        """
        if len(vectors) == 0:
            return []
            
        collection_name = self._get_collection_name(dataset_id)
        vector_size = vectors.shape[1]
        
        self._ensure_collection(collection_name, vector_size)
        
        points = []
        point_ids = []
        
        for i, vec in enumerate(vectors):
            # Tạo UUID ngẫu nhiên cho mỗi point
            pid = str(uuid.uuid4())
            point_ids.append(pid)
            
            # Đảm bảo payload khớp index (tránh lỗi out of bound)
            payload = payloads[i] if i < len(payloads) else {}
            
            points.append(PointStruct(
                id=pid,
                vector=vec.tolist(),
                payload=payload
            ))
            
        # Thực hiện Upsert theo batch
        self.client.upsert(
            collection_name=collection_name,
            points=points
        )
        
        logger.info(f"[VECTOR] Đã upsert {len(points)} points vào collection {collection_name}")
        return point_ids

    def search(
        self,
        dataset_id: str,
        query_vector: np.ndarray,
        top_k: int = 5,
        allowed_file_ids: Optional[List[str]] = None
    ) -> Tuple[List[float], List[Dict[str, Any]]]:
        """
        Tìm kiếm các vector tương đồng gần nhất (Similarity Search)
        
        Args:
            dataset_id: ID của bộ dữ liệu cần search
            query_vector: Vector câu hỏi (đã embed)
            top_k: Số lượng kết quả trả về
            allowed_file_ids: List ID của các file được phép search (Filter)
            
        Returns:
            Tuple: (List điểm số similarity, List metadata payloads)
        """
        collection_name = self._get_collection_name(dataset_id)
        
        # Kiểm tra collection tồn tại
        collections = self.client.get_collections().collections
        if not any(c.name == collection_name for c in collections):
            logger.warning(f"[VECTOR] Collection {collection_name} không tồn tại")
            return [], []
            
        vector_list = query_vector.tolist()
        if isinstance(vector_list[0], list):
             # Xử lý trường hợp input là 2D array (batch size 1)
             vector_list = vector_list[0]
        
        # Build Filter
        query_filter = None
        if allowed_file_ids is not None:
            # Nếu allowed_file_ids rỗng -> Không tìm thấy gì (logic chặt chẽ)
            if not allowed_file_ids:
                return [], []
                
            query_filter = rest.Filter(
                must=[
                    rest.FieldCondition(
                        key="dataset_file_id",
                        match=rest.MatchAny(any=allowed_file_ids)
                    )
                ]
            )

        try:
            # Use query_points (Qdrant 1.16+ API)
            # Docs: https://python-client.qdrant.tech/
            from qdrant_client.models import QueryRequest, VectorInput
            
            search_result = self.client.query_points(
                collection_name=collection_name,
                query=vector_list,
                query_filter=query_filter,
                limit=top_k,
                with_payload=True
            ).points
            
        except AttributeError as e:
            logger.error(f"[VECTOR] API Error: {e}. Trying legacy search method...")
            # Fallback to legacy search() if query_points() not available
            try:
                search_result = self.client.search(
                    collection_name=collection_name,
                    query_vector=vector_list,
                    query_filter=query_filter,
                    limit=top_k
                )
            except Exception as fallback_err:
                logger.error(f"[VECTOR] Fallback also failed: {fallback_err}")
                return [], []
        except Exception as e:
            logger.error(f"[VECTOR] Search Failed: {e}")
            return [], []
        
        # Tách kết quả thành 2 list riêng biệt
        scores = [hit.score for hit in search_result]
        payloads = [hit.payload for hit in search_result]
        
        return scores, payloads

    def delete_index(self, dataset_id: str):
        """Xóa toàn bộ collection (Dọn dẹp dữ liệu)"""
        collection_name = self._get_collection_name(dataset_id)
        try:
            self.client.delete_collection(collection_name=collection_name)
            logger.info(f"[VECTOR] Đã xóa collection {collection_name}")
        except Exception as e: 
            # Bỏ qua nếu không tìm thấy collection để xóa
            logger.warning(f"[VECTOR] Lỗi khi xóa collection (có thể không tồn tại): {e}")


# Singleton instance toàn cục
vector_service = VectorService()
