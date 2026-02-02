"""
Dataset Service - Xử lý nghiệp vụ cho Dataset
Service này chịu trách nhiệm thêm/sửa/xóa dataset, quản lý file và phân quyền.
"""
from app.repositories.dataset_repository import DatasetRepository
from app.repositories.dataset_file_repository import DatasetFileRepository
from app.repositories.file_repository import FileRepository
from app.repositories.chunk_repository import ChunkRepository
from app.services.vector_service import vector_service
from app.models.enums import FileStatus
from typing import List, Optional, Dict
import logging

logger = logging.getLogger(__name__)


class DatasetService:
    """Service xử lý nghiệp vụ cho datasets"""
    
    def __init__(
        self,
        dataset_repo: DatasetRepository,
        dataset_file_repo: DatasetFileRepository,
        file_repo: FileRepository,
        chunk_repo: ChunkRepository
    ):
        self.dataset_repo = dataset_repo
        self.dataset_file_repo = dataset_file_repo
        self.file_repo = file_repo
        self.chunk_repo = chunk_repo
    
    async def create_dataset(
        self,
        name: str,
        # config removed
        owner_id: str,
        visibility: str = "private",
        chatbot_ids: Optional[List[str]] = None
    ) -> dict:
        """
        Tạo dataset mới và tự động gán vào chatbots (nếu có)
        
        Logic:
            1. Validate tên (tối thiểu 3 ký tự)
            2. Gọi repository để lưu vào DB
            3. Nếu có chatbot_ids, assign dataset vào các chatbot đó
            
        Args:
            name: Tên bộ dữ liệu
            owner_id: ID người tạo (Teacher)
            visibility: Chế độ hiển thị (private/public)
            chatbot_ids: Danh sách chatbot IDs để gán dataset vào
        """
        if not name or len(name) < 3:
            raise ValueError("Tên bộ dữ liệu phải có ít nhất 3 ký tự")
        
        dataset = await self.dataset_repo.create_dataset(
            name, owner_id, visibility
        )
        
        # ✅ AUTO-ASSIGN: Gán dataset vào chatbots được chọn
        if chatbot_ids and len(chatbot_ids) > 0:
            from app.repositories.chatbot_repository import ChatbotRepository
            
            # Use same db instance as dataset_repo
            chatbot_repo = ChatbotRepository(self.dataset_repo.db)
            
            dataset_id = dataset["id"]
            for chatbot_id in chatbot_ids:
                try:
                    # Get current dataset_ids of chatbot
                    chatbot = await chatbot_repo.get_by_id(chatbot_id)
                    if chatbot:
                        current_datasets = chatbot.get("dataset_ids", [])
                        if current_datasets is None:
                            current_datasets = []
                        
                        # Add new dataset if not already present
                        if dataset_id not in current_datasets:
                            current_datasets.append(dataset_id)
                            await chatbot_repo.assign_datasets(chatbot_id, current_datasets)
                            logger.info(f"✅ Assigned dataset {dataset_id} to chatbot {chatbot_id}")
                except Exception as e:
                    logger.warning(f"Failed to assign dataset to chatbot {chatbot_id}: {e}")
        
        return dataset
    
    async def update_dataset(self, dataset_id: str, update_data: Dict) -> Optional[dict]:
        """Cập nhật thông tin dataset"""
        # Ensure config is not passed to update
        if "config" in update_data:
            del update_data["config"]
        return await self.dataset_repo.update_dataset(dataset_id, update_data)

    async def get_dataset(self, dataset_id: str) -> Optional[dict]:
        """Lấy chi tiết dataset theo ID"""
        return await self.dataset_repo.get_by_id(dataset_id)
    
    async def list_datasets(self) -> List[dict]:
        """Lấy danh sách toàn bộ datasets (Dành cho Admin)"""
        return await self.dataset_repo.get_all()
    
    async def list_datasets_by_owner(self, owner_id: str) -> List[dict]:
        """Lấy danh sách datasets do user sở hữu (Teacher)"""
        return await self.dataset_repo.get_by_owner(owner_id)
    
    async def list_datasets_shared_with(self, user_id: str) -> List[dict]:
        """Lấy danh sách datasets được chia sẻ với user (Student)"""
        return await self.dataset_repo.get_shared_with_user(user_id)
    
    async def share_dataset(self, dataset_id: str, user_ids: List[str]) -> bool:
        """
        Chia sẻ dataset cho danh sách users
        Cập nhật mảng shared_with trong DB
        """
        return await self.dataset_repo.share_dataset(dataset_id, user_ids)
    
    async def delete_dataset(self, dataset_id: str) -> bool:
        """
        Xóa dataset hoàn toàn và dọn dẹp dữ liệu liên quan
        
        Quy trình cleanup:
            1. Xóa records trong bảng dataset_files
            2. Xóa tất cả chunks trong MongoDB
            3. Xóa index vector tương ứng trong Qdrant (Vector DB)
            4. Xóa record dataset chính
        """
        # B1: Xóa quan hệ file-dataset
        await self.dataset_file_repo.delete_by_dataset(dataset_id)
        
        # B2: Xóa chunks dữ liệu
        await self.chunk_repo.delete_by_dataset(dataset_id)
        
        # B3: Xóa vector index
        vector_service.delete_index(dataset_id)
        
        # B4: Xóa dataset
        return await self.dataset_repo.delete_dataset(dataset_id)
    
    async def add_files_to_dataset(
        self,
        dataset_id: str,
        file_ids: List[str]
    ) -> Dict[str, List]:
        """
        Thêm files vào dataset
        
        Logic:
            - Kiểm tra dataset tồn tại
            - Kiểm tra từng file xem có tồn tại và trạng thái READY không
            - Tạo liên kết trong bảng dataset_files
            
        Returns:
             Dict chứa danh sách 'added' (thành công) và 'skipped' (thất bại)
        """
        added = []
        skipped = []
        
        # Kiểm tra dataset tồn tại
        dataset = await self.dataset_repo.get_by_id(dataset_id)
        if not dataset:
            raise ValueError(f"Không tìm thấy Dataset ID: {dataset_id}")
        
        # Lấy thông tin files
        files = await self.file_repo.get_by_ids(file_ids)
        files_map = {f["id"]: f for f in files}
        
        for file_id in file_ids:
            file_doc = files_map.get(file_id)
            
            # Chỉ thêm nếu file tồn tại và đã xử lý xong (READY)
            if not file_doc or file_doc.get("status") != FileStatus.READY.value:
                skipped.append({
                    "file_id": file_id,
                    "reason": "File không tồn tại hoặc chưa sẵn sàng"
                })
                continue
            
            # Tạo liên kết dataset-file
            df = await self.dataset_file_repo.create_dataset_file(
                dataset_id, 
                file_id
            )
            
            added.append(df)
        
        return {"added": added, "skipped": skipped}
    
    async def get_dataset_files(self, dataset_id: str) -> List[dict]:
        """Lấy danh sách files trong dataset kèm thông tin chi tiết (tên, size)"""
        dataset_files = await self.dataset_file_repo.get_by_dataset(dataset_id)
        if not dataset_files:
            return []
            
        # Lấy thông tin file gốc để merge vào kết quả
        file_ids = [df["file_id"] for df in dataset_files]
        files = await self.file_repo.get_by_ids(file_ids)
        files_map = {f["id"]: f for f in files}
        
        result = []
        for df in dataset_files:
            file_doc = files_map.get(df["file_id"])
            if file_doc:
                df["file_name"] = file_doc.get("name")
                df["file_size"] = file_doc.get("size")
            result.append(df)
            
        return result
    
    async def toggle_dataset_file(
        self,
        dataset_file_id: str,
        is_enabled: bool
    ) -> bool:
        """Bật/tắt việc sử dụng file trong dataset (Enable/Disable Context)"""
        return await self.dataset_file_repo.set_enabled(
            dataset_file_id, 
            is_enabled
        )

    # Alias for API compatibility
    async def toggle_file_status(self, dataset_id: str, dataset_file_id: str, enabled: bool) -> bool:
         return await self.toggle_dataset_file(dataset_file_id, enabled)
    
    async def remove_file_from_dataset(
        self,
        dataset_id: str,
        dataset_file_id: str
    ) -> bool:
        """
        Gỡ bỏ file khỏi dataset
        
        Logic cleanup:
            1. Xóa các chunks dữ liệu liên quan đến dataset file này
            2. Xóa record liên kết
        """
        # Cleanup chunks
        await self.chunk_repo.delete_by_dataset_file(dataset_id, dataset_file_id)
        
        # Xóa record dataset file
        return await self.dataset_file_repo.delete_by_id(dataset_file_id)
    
    async def get_chunks(
        self,
        dataset_id: str,
        dataset_file_id: str
    ) -> List[dict]:
        """Lấy danh sách các chunks dữ liệu của một file trong dataset"""
        return await self.chunk_repo.get_by_dataset_file(dataset_id, dataset_file_id)
