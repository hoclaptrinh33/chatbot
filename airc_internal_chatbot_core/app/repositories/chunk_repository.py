"""
Chunk Repository - Data access cho text chunks
"""
import re  # Required for regex escape in search_by_text
from app.repositories.base_repository import BaseRepository
from app.models.database import Collections
from typing import Optional, List


class ChunkRepository(BaseRepository):
    """Repository cho Chunk operations"""
    
    def __init__(self, db):
        super().__init__(db, Collections.CHUNKS)
    
    async def create_chunk(
        self,
        dataset_id: str,
        dataset_file_id: str,
        file_id: str,
        chunk_index: int,
        text: str,
        vector_id: Optional[int] = None
    ) -> dict:
        """Tạo chunk mới"""
        doc = {
            "dataset_id": dataset_id,
            "dataset_file_id": dataset_file_id,
            "file_id": file_id,
            "chunk_index": chunk_index,
            "text": text,
            "vector_id": vector_id
        }
        doc_id = await self.insert_one(doc)
        doc["id"] = doc_id
        return doc

    async def create_chunks(
        self,
        dataset_id: str,
        dataset_file_id: str,
        file_id: str,
        texts: List[str],
        vectors: List[List[float]] = None
    ) -> List[str]:
        """Tạo nhiều chunks (batch insert)"""
        docs = []
        for i, text in enumerate(texts):
            doc = {
                "dataset_id": dataset_id,
                "dataset_file_id": dataset_file_id,
                "file_id": file_id,
                "chunk_index": i,
                "text": text,
                # vector_id is index in FAISS, usually sequential or managed by vector_service
                # For simplicity, we assume vector_service returns IDs or we query them later.
                # But ProcessingService is passing embeddings.tolist() as vectors param?
                # ProcessingService logic: vector_service.add_vectors(dataset_id, embeddings)
                # We need to coordinate IDs. 
                # Let's assume vector_id matches chunk_index if sequential? 
                # Usually FAISS returns IDs.
                # Re-reading ProcessingService: It does vector_service.add_vectors AFTER repo call.
                # So here vector_id is unknown yet?
                "vector_id": None 
            }
            # Add vector if provided (though FAISS/Qdrant manages vectors usually)
            # Keeping DB structure simple.
            docs.append(doc)
            
        if not docs:
            return []
            
        result = await self.collection.insert_many(docs)
        return [str(uid) for uid in result.inserted_ids]

    async def search_by_text(
        self, 
        query: str, 
        dataset_file_ids: List[str], 
        limit: int = 5
    ) -> List[dict]:
        """Tìm kiếm chunks bằng Text Regex (Fallback)"""
        # Advanced: Split query into keywords for AND match (mimics Google search)
        # "Đề cương thực tập" -> match "Đề" AND "cương" AND "thực" AND "tập"
        # Handles "Đề cương chi tiết thực tập"
        keywords = query.strip().split()
        if not keywords:
             return []
             
        regex_conditions = [
            {"text": {"$regex": re.escape(word), "$options": "i"}} 
            for word in keywords 
            if len(word) > 1 # Ignore single chars to be safe? Or keep all
        ]
        
        if not regex_conditions:
            # Only single chars? fallback to full query
            regex_conditions = [{"text": {"$regex": re.escape(query), "$options": "i"}}]
            
        filter_doc = {
            "dataset_file_id": {"$in": dataset_file_ids},
            "$and": regex_conditions
        }
        
        cursor = self.collection.find(filter_doc).limit(limit)
        docs = await cursor.to_list(length=limit)
        return self.serialize_docs(docs)
    
    async def get_by_dataset_file(
        self, 
        dataset_id: str, 
        dataset_file_id: str
    ) -> List[dict]:
        """Lấy tất cả chunks của dataset file"""
        docs = await self.find_many(
            {
                "dataset_id": dataset_id,
                "dataset_file_id": dataset_file_id
            },
            sort=[("chunk_index", 1)]
        )
        return self.serialize_docs(docs)
    
    async def get_by_ids(self, chunk_ids: List[str]) -> List[dict]:
        """Lấy chunks theo list ID (cho retrieval từ Qdrant)"""
        oids = [self.to_object_id(cid) for cid in chunk_ids]
        oids = [oid for oid in oids if oid]
        if not oids:
            return []
        
        docs = await self.find_many({"_id": {"$in": oids}})
        return self.serialize_docs(docs)

    async def get_by_vector_ids(
        self,
        dataset_id: str,
        vector_ids: List[int],
        enabled_df_ids: List[str]
    ) -> List[dict]:
        """[DEPRECATED] Lấy chunks theo vector IDs (FAISS)"""
        docs = await self.find_many({
            "dataset_id": dataset_id,
            "dataset_file_id": {"$in": enabled_df_ids},
            "vector_id": {"$in": vector_ids}
        })
        return self.serialize_docs(docs)
    
    async def update_vector_id(self, chunk_id: str, vector_id: int) -> bool:
        """Cập nhật vector_id cho chunk"""
        oid = self.to_object_id(chunk_id)
        if not oid:
            return False
        return await self.update_one({"_id": oid}, {"vector_id": vector_id})
    
    async def delete_by_dataset_file(
        self, 
        dataset_id: str, 
        dataset_file_id: str
    ) -> int:
        """Xóa tất cả chunks của dataset file"""
        return await self.delete_many({
            "dataset_id": dataset_id,
            "dataset_file_id": dataset_file_id
        })
    
    async def delete_by_dataset(self, dataset_id: str) -> int:
        """Xóa tất cả chunks của dataset"""
        return await self.delete_many({"dataset_id": dataset_id})
