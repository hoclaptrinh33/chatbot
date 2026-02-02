"""
Base Repository - Abstract base class cho tất cả repositories
"""
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection
from bson import ObjectId
from typing import Optional, List, Dict, Any


class BaseRepository:
    """Base repository với common CRUD operations"""
    
    def __init__(self, db: AsyncIOMotorDatabase, collection_name: str):
        """
        Khởi tạo repository
        
        Args:
            db: MongoDB database instance
            collection_name: Tên collection
        """
        self.db = db
        self.collection_name = collection_name
        self.collection: AsyncIOMotorCollection = db[collection_name]
    
    @staticmethod
    def to_object_id(id_str: str) -> Optional[ObjectId]:
        """
        Convert string to ObjectId
        
        Args:
            id_str: String ID
            
        Returns:
            ObjectId hoặc None nếu invalid
        """
        try:
            return ObjectId(id_str)
        except Exception:
            return None
    
    @staticmethod
    def serialize_doc(doc: Optional[Dict]) -> Optional[Dict]:
        """
        Serialize MongoDB document (convert ObjectId to string)
        
        Args:
            doc: MongoDB document
            
        Returns:
            Serialized document hoặc None
        """
        if not doc:
            return None
        if "_id" in doc:
            doc["id"] = str(doc["_id"])
            del doc["_id"]
        return doc
    
    @staticmethod
    def serialize_docs(docs: List[Dict]) -> List[Dict]:
        """
        Serialize list of MongoDB documents
        
        Args:
            docs: List of documents
            
        Returns:
            List of serialized documents
        """
        return [BaseRepository.serialize_doc(doc) for doc in docs if doc]
    
    async def insert_one(self, document: Dict) -> str:
        """
        Insert một document
        
        Args:
            document: Document data
            
        Returns:
            ID của document mới tạo
        """
        result = await self.collection.insert_one(document)
        return str(result.inserted_id)
    
    async def find_one(self, query: Dict) -> Optional[Dict]:
        """
        Tìm một document
        
        Args:
            query: Query filter
            
        Returns:
            Document hoặc None
        """
        return await self.collection.find_one(query)
    
    async def find_many(self, query: Dict, limit: int = 100) -> List[Dict]:
        """
        Tìm nhiều documents
        
        Args:
            query: Query filter
            limit: Giới hạn số lượng
            
        Returns:
            List of documents
        """
        cursor = self.collection.find(query).limit(limit)
        return await cursor.to_list(length=limit)
    
    async def update_one(self, query: Dict, update_data: Dict) -> bool:
        """
        Update một document
        
        Args:
            query: Query filter
            update_data: Data cần update
            
        Returns:
            True nếu update thành công
        """
        result = await self.collection.update_one(query, {"$set": update_data})
        return result.modified_count > 0
    
    async def delete_one(self, query: Dict) -> bool:
        """
        Xóa một document
        
        Args:
            query: Query filter
            
        Returns:
            True nếu xóa thành công
        """
        result = await self.collection.delete_one(query)
        return result.deleted_count > 0
    
    async def count(self, query: Dict) -> int:
        """
        Đếm số documents
        
        Args:
            query: Query filter
            
        Returns:
            Số lượng documents
        """
        return await self.collection.count_documents(query)
