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
        self._doc_converter = None

    @property
    def doc_converter(self):
        """Lazy-loading Docling DocumentConverter để tránh chiếm bộ nhớ RAM của API web chính"""
        if self._doc_converter is None:
            logger.info("Khởi tạo Docling DocumentConverter...")
            try:
                from docling.document_converter import DocumentConverter, PdfFormatOption
                from docling.datamodel.pipeline_options import PdfPipelineOptions
                from docling.datamodel.base_models import InputFormat
                
                # Cấu hình pipeline options để bóc tách hình ảnh
                pipeline_options = PdfPipelineOptions()
                pipeline_options.images_scale = 1.0  # Tối ưu hóa chất lượng ảnh và dung lượng ổ đĩa
                pipeline_options.generate_picture_images = True  # Bật trích xuất hình vẽ/ảnh
                pipeline_options.generate_page_images = False    # Tắt xuất toàn bộ trang dưới dạng ảnh (không cần thiết)
                
                self._doc_converter = DocumentConverter(
                    format_options={
                        InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
                    }
                )
                logger.info("Khởi tạo Docling DocumentConverter thành công với cấu hình trích xuất hình ảnh.")
            except Exception as e:
                logger.exception("Không thể khởi tạo Docling DocumentConverter")
                raise e
        return self._doc_converter

    async def process_dataset_file(self, dataset_id: str, dataset_file_id: str):
        """
        Quy trình xử lý file:
        1. Lấy thông tin file
        2. Xác định đường dẫn file trên đĩa cứng
        3. Trích xuất text (Extract bằng Docling)
        4. Chia nhỏ text (Chunking)
        5. Tạo vector embeddings (Embed)
        6. Lưu chunks vào DB và index vectors vào Qdrant
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
            
            # 2. Lấy thông tin File gốc (để biết đường dẫn)
            file_doc = await self.file_repo.get_by_id(df["file_id"])
            if not file_doc:
                raise ValueError(f"File {df['file_id']} không tồn tại")
            
            # 3. Xác định đường dẫn File trên đĩa cứng
            try:
                file_path = file_doc["path"]
                if not os.path.exists(file_path):
                     # Kiểm tra đường dẫn tương đối so với thư mục chạy hiện hành
                     if os.path.exists(os.path.join(os.getcwd(), file_path)):
                         file_path = os.path.join(os.getcwd(), file_path)
                     else:
                         raise FileNotFoundError(f"Không tìm thấy file trên đĩa: {file_path}")
            except Exception as e:
                raise ValueError(f"Lỗi xác định đường dẫn file: {str(e)}")
            
            # 4. Trích xuất Text (PDF/DOCX/PPTX/HTML/TXT) sử dụng Docling
            text = self._extract_text(file_path, file_doc["name"], dataset_file_id)
            if not text:
                raise ValueError("Không trích xuất được nội dung text từ file")
            
            # 5. Chunking (Chia nhỏ văn bản)
            from app.services.chunking_service import chunking_service
            
            # Modern chunking: 1024 chars với overlap 100 chars, preserve sentence boundaries
            chunks_dicts = chunking_service.chunk_text(
                text, 
                chunk_size=1024,      # Tối ưu hóa kích thước character-based cho tiếng Việt
                chunk_overlap=100,    # Overlap để giữ ngữ cảnh liền mạch
                preserve_sentences=True
            )
            
            # Extract text từ chunk dictionaries
            chunks_text = [chunk["text"] for chunk in chunks_dicts]
            
            logger.info(f"[PROCESS] Đã chia thành {len(chunks_text)} chunks")
            
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
            
            # 8. Hoàn tất -> Cập nhật trạng thái DONE và enabled = True
            await self.dataset_file_repo.update_status(
                dataset_file_id, 
                DatasetFileStatus.DONE,
                chunk_count=len(chunks_text)
            )
            
            await self.dataset_file_repo.set_enabled(dataset_file_id, True)
            
            logger.info(f"[PROCESS] Hoàn tất xử lý dataset_file={dataset_file_id}, is_enabled=True")
            
        except Exception as e:
            logger.exception(f"[PROCESS] Lỗi khi xử lý dataset_file={dataset_file_id}")
            # Cập nhật trạng thái ERROR nếu có lỗi
            await self.dataset_file_repo.update_status(dataset_file_id, DatasetFileStatus.ERROR)

    def _extract_text(self, file_path: str, filename: str, dataset_file_id: str = None) -> str:
        """Helper: Trích xuất text dựa trên định dạng file (Docling cho các định dạng được hỗ trợ)"""
        filename_lower = filename.lower()
        
        # Các định dạng Docling hỗ trợ tốt và cần giữ cấu trúc
        docling_supported_exts = (".pdf", ".docx", ".pptx", ".html")
        
        if any(filename_lower.endswith(ext) for ext in docling_supported_exts):
            logger.info(f"Sử dụng Docling để bóc tách tài liệu: {filename}")
            try:
                result = self.doc_converter.convert(file_path)
                
                # Trích xuất và lưu hình ảnh (chỉ chạy nếu là PDF và có truyền dataset_file_id)
                from docling_core.types.doc import PictureItem
                
                # Tạo thư mục lưu ảnh trích xuất: uploads/extracted_images/{dataset_file_id}
                img_dir = os.path.join("uploads", "extracted_images", dataset_file_id) if dataset_file_id else None
                if img_dir:
                    os.makedirs(img_dir, exist_ok=True)
                
                picture_counter = 0
                for element, _level in result.document.iterate_items():
                    if isinstance(element, PictureItem):
                        picture_counter += 1
                        if img_dir:
                            img_filename = f"image_{picture_counter}.png"
                            img_path = os.path.join(img_dir, img_filename)
                            try:
                                # Lấy ảnh PIL và lưu
                                pil_img = element.get_image(result.document)
                                pil_img.save(img_path, "PNG")
                                logger.info(f"Đã lưu ảnh trích xuất thành công: {img_path}")
                            except Exception as img_err:
                                logger.error(f"Lỗi khi lưu ảnh trích xuất {img_filename}: {img_err}")
                
                # Xuất ra định dạng Markdown
                markdown_content = result.document.export_to_markdown()
                
                # Thay thế các tag <!-- image --> trong Markdown bằng đường dẫn ảnh thật
                # Thay thế lần lượt theo thứ tự xuất hiện của PictureItem
                if picture_counter > 0 and dataset_file_id:
                    parts = markdown_content.split("<!-- image -->")
                    replaced_content = parts[0]
                    for i in range(1, len(parts)):
                        img_filename = f"image_{i}.png"
                        img_path_rel = f"/uploads/extracted_images/{dataset_file_id}/{img_filename}"
                        replaced_content += f"![Hình ảnh {i}]({img_path_rel})" + parts[i]
                    markdown_content = replaced_content
                    logger.info(f"Đã cập nhật {picture_counter} liên kết hình ảnh tĩnh vào Markdown.")
                
                return markdown_content
            except Exception as e:
                logger.error(f"Lỗi khi trích xuất bằng Docling cho {filename}: {str(e)}")
                # Chạy cơ chế fallback nếu Docling gặp sự cố
                return self._fallback_extract(file_path, filename_lower)
        elif filename_lower.endswith(".txt"):
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    return f.read()
            except Exception as e:
                raise ValueError(f"Lỗi đọc file TXT từ đĩa: {str(e)}")
        else:
            raise ValueError(f"Định dạng file không hỗ trợ: {filename}")

    def _fallback_extract(self, file_path: str, filename_lower: str) -> str:
        """Hàm fallback sử dụng pypdf hoặc python-docx cũ khi Docling gặp lỗi"""
        logger.warning(f"Bắt đầu cơ chế fallback trích xuất cho file: {file_path}")
        try:
            if filename_lower.endswith(".pdf"):
                text = ""
                with open(file_path, "rb") as f:
                    pdf = pypdf.PdfReader(f)
                    for page in pdf.pages:
                        text += page.extract_text() + "\n"
                return text
            elif filename_lower.endswith(".docx"):
                doc_file = docx.Document(file_path)
                return "\n".join([para.text for para in doc_file.paragraphs])
        except Exception as e:
            logger.error(f"Cơ chế fallback trích xuất thất bại: {str(e)}")
        return ""

