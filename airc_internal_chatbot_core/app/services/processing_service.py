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

    def _create_doc_converter(self, do_ocr: bool = False):
        """Tạo DocumentConverter. OCR tắt mặc định vì EasyOCR tải model rất chậm và không cần cho PDF số hóa."""
        from docling.document_converter import DocumentConverter, PdfFormatOption
        from docling.datamodel.pipeline_options import PdfPipelineOptions, EasyOcrOptions
        from docling.datamodel.base_models import InputFormat

        pipeline_options = PdfPipelineOptions()
        pipeline_options.images_scale = 1.0
        pipeline_options.generate_picture_images = False
        pipeline_options.generate_page_images = False
        pipeline_options.do_table_structure = True
        pipeline_options.table_structure_options.do_cell_matching = True
        pipeline_options.do_ocr = do_ocr
        if do_ocr:
            pipeline_options.ocr_options = EasyOcrOptions(lang=["vi", "en"])

        return DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )

    @property
    def doc_converter(self):
        """Lazy-loading Docling DocumentConverter để tránh chiếm bộ nhớ RAM của API web chính"""
        if self._doc_converter is None:
            logger.info("Khởi tạo Docling DocumentConverter (OCR tắt)...")
            try:
                self._doc_converter = self._create_doc_converter(do_ocr=False)
                logger.info("Khởi tạo Docling DocumentConverter thành công (bảng cấu trúc, không OCR).")
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
            await self.chunk_repo.delete_by_dataset_file(dataset_id, dataset_file_id)
            vector_service.delete_by_dataset_file(dataset_id, dataset_file_id)
            
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
            
            # 5. Sinh Document Summary (Tóm tắt tài liệu) phục vụ Rich Context
            document_summary = ""
            try:
                # Trích xuất một phần nội dung nếu quá dài để tránh tràn token của LLM
                summary_input = text
                if len(text) > 8000:
                    summary_input = text[:4000] + "\n...[PHẦN GIỮA ĐÃ ĐƯỢC LƯỢC BỎ]...\n" + text[-4000:]
                
                prompt = (
                    "Hãy tóm tắt ngắn gọn nội dung chính của tài liệu sau bằng Tiếng Việt trong vòng 100-150 từ. "
                    "Hãy tập trung vào chủ đề chính và các thông tin quan trọng nhất để làm ngữ cảnh tìm kiếm. "
                    "Chỉ trả về nội dung tóm tắt thô, không thêm bất cứ lời dẫn nào như 'Dưới đây là tóm tắt' hoặc 'Tóm tắt:'.\n\n"
                    f"Nội dung tài liệu:\n{summary_input}"
                )
                from app.services.llm_service import llm_service
                logger.info(f"[PROCESS] Đang sinh Document Summary cho file {file_doc['name']}...")
                # Thiết lập timeout ngắn tránh treo hàng đợi
                document_summary = await llm_service.generate(
                    prompt=prompt,
                    temperature=0.3,
                    max_tokens=256
                )
                if any(err in document_summary for err in ["Lỗi Server AI", "Không thể kết nối", "Thời gian yêu cầu"]):
                    logger.warning(f"[PROCESS] Không sinh được summary do lỗi LLM: {document_summary}")
                    document_summary = ""
                else:
                    document_summary = document_summary.strip()
                    logger.info(f"[PROCESS] Đã sinh Document Summary thành công: {document_summary[:100]}...")
            except Exception as sum_err:
                logger.warning(f"[PROCESS] Bỏ qua sinh tóm tắt do gặp lỗi: {sum_err}")
                document_summary = ""

            # Phân loại tài liệu động dựa trên tên file
            filename_lower = file_doc["name"].lower()
            file_type = "general"
            if any(k in filename_lower for k in ["quy che", "quy chế", "dieu khoan", "điều khoản", "luat", "luật", "nghi dinh", "nghị định", "thong tu", "thông tư", "quy dinh", "quy định", "chinh sach", "chính sách"]):
                file_type = "legal"
            elif any(k in filename_lower for k in ["bao cao", "báo cáo", "tai chinh", "tài chính", "doanh thu", "ket qua", "kết quả"]):
                file_type = "financial"
            elif any(k in filename_lower for k in ["faq", "hoi dap", "hỏi đáp", "q&a", "qa"]):
                file_type = "faq"

            # 6. Chunking (Chia nhỏ văn bản nâng cấp)
            from app.services.chunking_service import chunking_service
            chunks_data = chunking_service.chunk_document_advanced(
                text=text,
                filename=file_doc["name"],
                document_summary=document_summary,
                file_type=file_type
            )
            
            logger.info(f"[PROCESS] Đã chia thành {len(chunks_data)} chunks (bao gồm cả parent & child) với loại {file_type}")
            
            # Phân tách Parent và Child chunks
            parent_indices_with_children = set(
                c["parent_chunk_temp_idx"] for c in chunks_data if "parent_chunk_temp_idx" in c
            )
            
            chunks_to_embed = [
                c for c in chunks_data 
                if not (c["is_parent"] and c["chunk_index"] in parent_indices_with_children)
            ]
            
            # Cập nhật trạng thái -> EMBEDDING
            await self.dataset_file_repo.update_status(dataset_file_id, DatasetFileStatus.EMBEDDING)
            
            # 7. Embedding (Tạo vectors cho child/độc lập chunks)
            enriched_texts_to_embed = [c["context_enriched_text"] for c in chunks_to_embed]
            embeddings = embedding_service.embed_texts(enriched_texts_to_embed)
            
            # 8. Lưu trữ Chunks & Vectors vào DB
            # Bước A: Lưu Parent Chunks trước để lấy ID thật từ MongoDB
            parent_chunks = [
                c for c in chunks_data 
                if c["is_parent"] and c["chunk_index"] in parent_indices_with_children
            ]
            
            temp_idx_to_real_id = {}
            if parent_chunks:
                parent_ids = await self.chunk_repo.create_chunks(
                    dataset_id=dataset_id,
                    dataset_file_id=dataset_file_id,
                    file_id=df["file_id"],
                    chunks_data=parent_chunks
                )
                temp_idx_to_real_id = {
                    parent_chunks[i]["chunk_index"]: parent_ids[i]
                    for i in range(len(parent_chunks))
                }
                
            # Bước B: Gán parent_chunk_id thật cho các Child chunks
            for c in chunks_to_embed:
                temp_parent_idx = c.get("parent_chunk_temp_idx")
                if temp_parent_idx is not None and temp_parent_idx in temp_idx_to_real_id:
                    c["parent_chunk_id"] = temp_idx_to_real_id[temp_parent_idx]
                else:
                    c["parent_chunk_id"] = None
            
            # Bước C: Lưu các chunks_to_embed (child & độc lập) vào MongoDB
            embeddable_chunk_ids = await self.chunk_repo.create_chunks(
                dataset_id=dataset_id,
                dataset_file_id=dataset_file_id,
                file_id=df["file_id"],
                chunks_data=chunks_to_embed
            )
            
            # Map chunk_ids với payloads tương ứng cho Qdrant
            payloads = [
                {
                    "chunk_id": str(embeddable_chunk_ids[i]),
                    "dataset_file_id": dataset_file_id,
                    "dataset_id": dataset_id,
                    "is_child": not chunks_to_embed[i]["is_parent"],
                    "parent_chunk_id": chunks_to_embed[i]["parent_chunk_id"],
                    "chunk_role": chunks_to_embed[i].get("chunk_role", "standalone"),
                    "domain": chunks_to_embed[i].get("domain", "general"),
                    "language": chunks_to_embed[i].get("language", "vi"),
                    "is_table": chunks_to_embed[i].get("is_table", False)
                }
                for i in range(len(chunks_to_embed))
            ]
            
            # Index vectors vào Qdrant
            vector_service.add_vectors(dataset_id, embeddings, payloads)
            
            # 9. Hoàn tất -> Cập nhật trạng thái DONE và enabled = True
            await self.dataset_file_repo.update_status(
                dataset_file_id, 
                DatasetFileStatus.DONE,
                chunk_count=len(chunks_to_embed)
            )
            
            await self.dataset_file_repo.set_enabled(dataset_file_id, True)
            
            logger.info(f"[PROCESS] Hoàn tất xử lý dataset_file={dataset_file_id}, is_enabled=True")
            
        except Exception as e:
            logger.exception(f"[PROCESS] Lỗi khi xử lý dataset_file={dataset_file_id}")
            # Cập nhật trạng thái ERROR nếu có lỗi
            await self.dataset_file_repo.update_status(dataset_file_id, DatasetFileStatus.ERROR)
            raise

    def _extract_text(self, file_path: str, filename: str, dataset_file_id: str = None) -> str:
        """Helper: Trích xuất text dựa trên định dạng file (Docling cho các định dạng được hỗ trợ)"""
        filename_lower = filename.lower()
        
        # Các định dạng Docling hỗ trợ tốt và cần giữ cấu trúc
        docling_supported_exts = (".pdf", ".docx", ".pptx", ".html")
        
        if any(filename_lower.endswith(ext) for ext in docling_supported_exts):
            logger.info(f"Sử dụng Docling để bóc tách tài liệu: {filename}")
            try:
                import time
                t0 = time.monotonic()
                result = self.doc_converter.convert(file_path)
                logger.info(
                    "Docling convert xong %s sau %.1fs",
                    filename,
                    time.monotonic() - t0,
                )
                
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

                # PDF số hóa đã có text layer: nếu Docling ra ít chữ thì dùng pypdf
                # thay vì bật EasyOCR (tải model có thể treo worker hàng giờ).
                if filename_lower.endswith(".pdf") and len((markdown_content or "").strip()) < 100:
                    fallback_text = self._fallback_extract(file_path, filename_lower)
                    if fallback_text and len(fallback_text.strip()) >= 100:
                        logger.warning(
                            "Docling trả về ít text nhưng pypdf đọc được %s ký tự; dùng fallback.",
                            len(fallback_text.strip()),
                        )
                        return fallback_text
                
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

