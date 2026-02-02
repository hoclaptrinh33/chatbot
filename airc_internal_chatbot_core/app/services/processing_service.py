"""
Processing Service - Xử lý File -> Text -> Vector -> Index
Service này xử lý luồng background để chuyển đổi các file tài liệu thành vectors và index vào Qdrant.
"""
from app.repositories import DatasetFileRepository, FileRepository, ChunkRepository
from app.services.vector_service import vector_service
from app.services.embedding_service import embedding_service
from app.models.enums import DatasetFileStatus
from typing import List
import logging
import io
import pypdf
import docx
from langchain_text_splitters import RecursiveCharacterTextSplitter
import aiofiles
import os

# Khởi tạo logger
logger = logging.getLogger(__name__)

# Local storage configuration (if needed)
# UPLOAD_DIR = "uploads"


class ProcessingService:
    """Service xử lý dữ liệu background"""
    
    def __init__(
        self,
        dataset_file_repo: DatasetFileRepository,
        file_repo: FileRepository,
        chunk_repo: ChunkRepository
    ):
        self.dataset_file_repo = dataset_file_repo
        self.file_repo = file_repo
        self.chunk_repo = chunk_repo

    async def process_dataset_file(self, dataset_id: str, dataset_file_id: str):
        """
        Quy trình xử lý file:
        1. Download file từ MinIO
        2. Trích xuất text (Extract)
        3. Chia nhỏ text (Chunking)
        4. Tạo vector embeddings (Embed)
        5. Lưu chunks vào DB và index vectors vào Qdrant
        """
        logger.info(f"[PROCESS] Bắt đầu xử lý dataset_file={dataset_file_id}")
        
        try:
            # 1. Lấy thông tin Dataset File
            df = await self.dataset_file_repo.get_by_id(dataset_file_id)
            if not df:
                logger.error(f"[PROCESS] DatasetFile {dataset_file_id} không tồn tại")
                return
            
            # Cập nhật trạng thái -> CHUNKING (Đang xử lý)
            await self.dataset_file_repo.update_status(dataset_file_id, DatasetFileStatus.CHUNKING)
            
            # 2. Lấy thông tin File gốc (để biết đường dẫn MinIO)
            file_doc = await self.file_repo.get_by_id(df["file_id"])
            if not file_doc:
                raise ValueError(f"File {df['file_id']} không tồn tại")
            
            # 3. Đọc nội dung từ Local Disk
            try:
                # Assuming file_doc["path"] is absolute or relative to app root
                # If relative, we need to ensure cwd is correct or prepend prefix
                file_path = file_doc["path"]
                if not os.path.exists(file_path):
                     # Try prefixing with app root if needed, but path stored was relative e.g. "uploads/..."
                     if os.path.exists(os.path.join(os.getcwd(), file_path)):
                         file_path = os.path.join(os.getcwd(), file_path)
                     else:
                         raise FileNotFoundError(f"File not found on disk: {file_path}")

                async with aiofiles.open(file_path, 'rb') as f:
                    file_content = await f.read()
            except Exception as e:
                raise ValueError(f"Lỗi đọc file từ ổ cứng: {str(e)}")
            
            # 4. Trích xuất Text (PDF/DOCX/TXT)
            text = self._extract_text(file_content, file_doc["name"])
            if not text:
                raise ValueError("Không trích xuất được nội dung text từ file")
            
            # 5. Chunking (Chia nhỏ văn bản)
            # Fix: Sử dụng Modern Chunking Service tối ưu cho tiếng Việt
            # Thay vì legacy word-based split (200 words), dùng character-based với Vietnamese separators
            from app.services.chunking_service import chunking_service
            
            # Modern chunking: 1024 chars với overlap 100 chars, preserve sentence boundaries
            # Tốt hơn legacy vì:
            # - Recursive splitting theo dấu câu Vietnamese (\n\n, \n, . ! ? ; : ,)
            # - Giữ nguyên câu trọn vẹn (preserve_sentences)
            # - Chunk size lớn hơn -> context tốt hơn cho embedding
            chunks_dicts = chunking_service.chunk_text(
                text, 
                chunk_size=1024,      # Character-based, tối ưu cho Vietnamese SBERT
                chunk_overlap=100,    # 10% overlap để giữ context
                preserve_sentences=True
            )
            
            # Extract text từ chunk dictionaries
            chunks_text = [chunk["text"] for chunk in chunks_dicts]
            
            logger.info(f"[PROCESS] Đã chia thành {len(chunks_text)} chunks (Modern Vietnamese Chunking)")
            
            # Cập nhật trạng thái -> EMBEDDING
            await self.dataset_file_repo.update_status(dataset_file_id, DatasetFileStatus.EMBEDDING)
            
            # 6. Embedding (Tạo vectors)
            embeddings = embedding_service.embed_texts(chunks_text)
            
            # 7. Lưu trữ Chunks & Vectors
            # Lưu chunks vào MongoDB
            chunk_ids = await self.chunk_repo.create_chunks(
                dataset_id=dataset_id,
                dataset_file_id=dataset_file_id,
                file_id=df["file_id"],
                texts=chunks_text,
                vectors=embeddings.tolist()
            )
            
            # Map chunk_ids với payloads tương ứng cho Qdrant
            payloads = [
                {
                    "chunk_id": str(cid),
                    "dataset_file_id": dataset_file_id,
                    "dataset_id": dataset_id
                }
                for cid in chunk_ids
            ]
            
            # Index vectors vào Qdrant
            vector_service.add_vectors(dataset_id, embeddings, payloads)
            
            # 8. Hoàn tất -> Cập nhật trạng thái DONE và đảm bảo is_enabled = True
            await self.dataset_file_repo.update_status(
                dataset_file_id, 
                DatasetFileStatus.DONE,
                chunk_count=len(chunks_text)
            )
            
            # Đảm bảo file được enabled để có thể search được ngay lập tức
            # Fix: Ngăn chặn trường hợp file bị disable sau khi ingest xong
            await self.dataset_file_repo.set_enabled(dataset_file_id, True)
            
            logger.info(f"[PROCESS] Hoàn tất xử lý dataset_file={dataset_file_id}, is_enabled=True")
            
        except Exception as e:
            logger.exception(f"[PROCESS] Lỗi khi xử lý dataset_file={dataset_file_id}")
            # Cập nhật trạng thái ERROR nếu có lỗi
            await self.dataset_file_repo.update_status(dataset_file_id, DatasetFileStatus.ERROR)

    def _extract_text(self, content: bytes, filename: str) -> str:
        """Helper: Trích xuất text dựa trên định dạng file"""
        filename = filename.lower()
        
        if filename.endswith(".pdf"):
            return self._extract_pdf(content)
        elif filename.endswith(".docx"):
            return self._extract_docx(content)
        elif filename.endswith(".txt"):
            return content.decode("utf-8", errors="ignore")
        else:
            raise ValueError(f"Định dạng file không hỗ trợ: {filename}")

    def _extract_pdf(self, content: bytes) -> str:
        """Trích xuất text từ PDF"""
        text = ""
        with io.BytesIO(content) as f:
            pdf = pypdf.PdfReader(f)
            for page in pdf.pages:
                text += page.extract_text() + "\n"
        return text

    def _extract_docx(self, content: bytes) -> str:
        """Trích xuất text từ DOCX"""
        with io.BytesIO(content) as f:
            doc = docx.Document(f)
            return "\n".join([para.text for para in doc.paragraphs])
