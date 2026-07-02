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
        texts: List[str] = None,
        vectors: List[List[float]] = None,
        chunks_data: List[dict] = None
    ) -> List[str]:
        """
        Tạo nhiều chunks (batch insert).
        Hỗ trợ cấu trúc Parent-Child và Rich Context.
        """
        docs = []
        if chunks_data:
            for chunk in chunks_data:
                doc = {
                    "dataset_id": dataset_id,
                    "dataset_file_id": dataset_file_id,
                    "file_id": file_id,
                    "chunk_index": chunk.get("chunk_index"),
                    "text": chunk.get("text"),
                    "context_enriched_text": chunk.get("context_enriched_text"),
                    "heading_path": chunk.get("heading_path", []),
                    "is_parent": chunk.get("is_parent", False),
                    "parent_chunk_id": chunk.get("parent_chunk_id"),
                    "vector_id": chunk.get("vector_id")
                }
                docs.append(doc)
        else:
            # Fallback cơ chế cũ chỉ truyền texts
            for i, text in enumerate(texts or []):
                doc = {
                    "dataset_id": dataset_id,
                    "dataset_file_id": dataset_file_id,
                    "file_id": file_id,
                    "chunk_index": i,
                    "text": text,
                    "context_enriched_text": text,
                    "heading_path": [],
                    "is_parent": False,
                    "parent_chunk_id": None,
                    "vector_id": None 
                }
                docs.append(doc)
            
        if not docs:
            return []
            
        result = await self.collection.insert_many(docs)
        return [str(uid) for uid in result.inserted_ids]

    async def get_parent_chunks_by_ids(self, parent_ids: List[str]) -> List[dict]:
        """Lấy danh sách các chunk cha theo danh sách ID"""
        oids = [self.to_object_id(pid) for pid in parent_ids if pid]
        oids = [oid for oid in oids if oid]
        if not oids:
            return []
        
        docs = await self.find_many({"_id": {"$in": oids}})
        return self.serialize_docs(docs)

    async def create_chunks_advanced(
        self,
        dataset_id: str,
        dataset_file_id: str,
        file_id: str,
        chunks: List[dict]
    ) -> List[dict]:
        """
        Tạo nhiều chunks với cấu trúc nâng cao (Parent-Child, Heading Path, Context Enriched)
        """
        if not chunks:
            return []
            
        # 1. Tách và chèn các Parent Chunks trước để lấy ObjectId
        parent_chunks = [c for c in chunks if c.get("is_parent") is True]
        parent_map = {} # map chunk_index -> Mongo ID string
        
        for p_chunk in parent_chunks:
            doc = {
                "dataset_id": dataset_id,
                "dataset_file_id": dataset_file_id,
                "file_id": file_id,
                "chunk_index": p_chunk["chunk_index"],
                "text": p_chunk["text"],
                "context_enriched_text": p_chunk.get("context_enriched_text", p_chunk["text"]),
                "heading_path": p_chunk.get("heading_path", []),
                "is_parent": True,
                "parent_chunk_id": None,
                "vector_id": None
            }
            inserted_id = await self.insert_one(doc)
            p_chunk["id"] = inserted_id
            parent_map[p_chunk["chunk_index"]] = inserted_id
            
        # 2. Chuẩn bị chèn các Child Chunks và các Chunks độc lập
        other_chunks = [c for c in chunks if not c.get("is_parent")]
        docs_to_insert = []
        
        for c_chunk in other_chunks:
            p_idx = c_chunk.get("parent_chunk_index")
            p_id = parent_map.get(p_idx) if p_idx is not None else None
            
            doc = {
                "dataset_id": dataset_id,
                "dataset_file_id": dataset_file_id,
                "file_id": file_id,
                "chunk_index": c_chunk["chunk_index"],
                "text": c_chunk["text"],
                "context_enriched_text": c_chunk.get("context_enriched_text", c_chunk["text"]),
                "heading_path": c_chunk.get("heading_path", []),
                "is_parent": False,
                "parent_chunk_id": p_id,
                "vector_id": None
            }
            docs_to_insert.append((c_chunk, doc))
            
        if docs_to_insert:
            # Thực hiện chèn nhiều tài liệu cùng lúc
            insert_payloads = [doc for _, doc in docs_to_insert]
            result = await self.collection.insert_many(insert_payloads)
            
            # Map ngược lại ObjectId cho từng chunk
            for i, inserted_id in enumerate(result.inserted_ids):
                chunk_obj, _ = docs_to_insert[i]
                chunk_obj["id"] = str(inserted_id)
                # Cập nhật trường parent_chunk_id trong chunk_obj để trả về
                p_idx = chunk_obj.get("parent_chunk_index")
                chunk_obj["parent_chunk_id"] = parent_map.get(p_idx) if p_idx is not None else None
                
        # Trả về danh sách chunks ban đầu đã được gán id
        return chunks


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
