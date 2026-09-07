"""
Chat Service - Business Logic for RAG Chatbot
Service này xử lý toàn bộ luồng nghiệp vụ của chức năng Chat:
1. Retrieval: Tìm kiếm context từ Vector DB (Qdrant)
2. Rerank: Sắp xếp lại kết quả tìm kiếm để tối ưu độ chính xác
3. Generation: Sử dụng LLM (Gemini) để sinh câu trả lời
4. Caching: Cache kết quả để tăng tốc độ phản hồi
"""
import logging
import time
from typing import List, Dict, Optional, Any, Tuple, Awaitable, Callable
import numpy as np

from app.repositories.dataset_repository import DatasetRepository
from app.repositories.dataset_file_repository import DatasetFileRepository
from app.repositories.chunk_repository import ChunkRepository
from app.repositories.file_repository import FileRepository
from app.services.embedding_service import embedding_service
from app.services.vector_service import vector_service
from app.services.llm_service import llm_service
from app.services.prompt_service import prompt_service
from app.services.rerank_service import rerank_service
from app.services.cache_service import semantic_cache_service
from app.services.cache_policy import is_cacheable_answer
from app.services.retrieval_merge import apply_score_threshold, rrf_merge
from app.core.config import settings

logger = logging.getLogger(__name__)

# Constants
DEFAULT_TOP_K = 5
MAX_DATASETS_PER_REQUEST = 8


class ChatService:
    """
    Lớp xử lý nghiệp vụ Chat RAG (Retrieval-Augmented Generation).
    Áp dụng Dependency Injection cho các Repositories.
    """
    
    def __init__(
        self,
        dataset_repo: DatasetRepository,
        dataset_file_repo: DatasetFileRepository,
        chunk_repo: ChunkRepository,
        session_repo: Any = None,
        chatbot_repo: Any = None,
        file_repo: Any = None,
    ):
        self.dataset_repo = dataset_repo
        self.dataset_file_repo = dataset_file_repo
        self.chunk_repo = chunk_repo
        self.session_repo = session_repo
        self.chatbot_repo = chatbot_repo
        self.file_repo = file_repo
    
    async def ask_question(
        self,
        question: str,
        dataset_ids: List[str],
        history: Optional[List[Dict]] = None,
        session_id: Optional[str] = None,
        chatbot_id: Optional[str] = None, # NEW: Chatbot ID
        user_context: Optional[Dict] = None, # NEW: User Context for RBAC
        stream_callback: Optional[Callable[[str], Awaitable[None]]] = None,
    ) -> Dict[str, Any]:
        """
        Xử lý câu hỏi của người dùng theo quy trình RAG chuẩn.
        Hỗ trợ lưu lịch sử nếu có session_id.
        """
        # ═══════════════════════════════════════════════════════════════
        # 🔍 DEBUG METRICS - Track performance at each stage
        # ═══════════════════════════════════════════════════════════════
        debug_metrics = {
            "total_time_ms": 0,
            "embedding_time_ms": 0,
            "retrieval_time_ms": 0,
            "rerank_time_ms": 0,
            "llm_time_ms": 0,
            "cache_hit": False,
            "chunks_found": 0,
            "chunks_after_rerank": 0,
            "avg_similarity_score": 0.0,
            "top_similarity_score": 0.0,
            "datasets_searched": 0,
            "model_used": None,
            "reranker_used": None,
            "no_context": False,
            "search_mode": "hybrid",
            "similarity_threshold": 0.25,
        }
        start_total = time.time()
        
        # 0. Handle Session & History
        conversation_summary = None
        if session_id and self.session_repo:
            # Save User Message first
            await self.session_repo.add_message(session_id, "user", question)
            
            # Load session summary
            session_doc = await self.session_repo.get_session(session_id)
            if session_doc:
                conversation_summary = session_doc.get("conversation_summary")
            
            # If history not provided, load from session
            if not history:
                db_messages = await self.session_repo.get_messages(session_id)
                history = [
                    {"role": m["role"], "content": m["content"]} 
                    for m in db_messages
                    if m["role"] in ["user", "assistant"]
                ]

        # 1. Validation & Setup
        if not question:
            raise ValueError("Câu hỏi không được để trống")
        
        dataset_ids = dataset_ids[:MAX_DATASETS_PER_REQUEST] if dataset_ids else []
        logger.info(
            "[CHAT] Xử lý câu hỏi: '%s...' | Datasets: %s | Session: %s | cache=%s fast_path=%s",
            question[:50],
            len(dataset_ids),
            session_id,
            settings.semantic_cache_enabled,
            settings.chat_fast_path,
        )

        # 2. Check Semantic Cache (Tối ưu performance)
        # CRITICAL: Cache key MUST include chatbot_id to prevent cross-bot pollution
        start_embed = time.time()
        q_embedding = self._try_embed_question(question)
        debug_metrics["embedding_time_ms"] = round((time.time() - start_embed) * 1000, 2)
        
        cache_key_suffix = f"_bot_{chatbot_id}" if chatbot_id else ""
        
        if settings.semantic_cache_enabled and q_embedding is not None:
            cached_resp = semantic_cache_service.get(question, q_embedding, suffix=cache_key_suffix)
            if cached_resp:
                logger.info(f"[CHAT] Cache HIT (chatbot={chatbot_id}) - Trả về kết quả đã lưu.")
                # Save cached answer if session exists
                assistant_message_id = None
                if session_id and self.session_repo:
                    saved = await self.session_repo.add_message(
                        session_id,
                        "assistant",
                        cached_resp,
                        extra={"latency_ms": 0, "cached": True},
                    )
                    assistant_message_id = saved.get("id")
                if stream_callback:
                    await stream_callback(cached_resp)
                
                debug_metrics["cache_hit"] = True
                debug_metrics["total_time_ms"] = round((time.time() - start_total) * 1000, 2)
                return self._format_response(
                    question, cached_resp, [], [], cached=True,
                    debug_metrics=debug_metrics, message_id=assistant_message_id,
                )

        # 3. Retrieval Process (Tìm kiếm dữ liệu từ Datasets)
        # Determine RAG Config
        rag_top_k = DEFAULT_TOP_K
        rag_reranker = None
        rag_threshold = 0.25
        
        # 0.5 Fetch Chatbot Config & Enforce Context
        rag_api_key = None
        rag_api_base_url = None
        rag_model = None
        rag_system_prompt = None
        rag_temperature = 0.7
        rag_max_tokens = 2048
        
        # Default: fast bot (no extra LLM hops). Accuracy bots opt in via config.
        enable_query_reformulation = False
        enable_history_compression = False
        rag_search_mode = "hybrid"
        history_limit = 3
        buffer_limit = 2
        compression_model = "gemini-1.5-flash"
        
        if chatbot_id and self.chatbot_repo:
            chatbot = await self.chatbot_repo.get_by_id(chatbot_id)
            if chatbot:
                # 0.6 RBAC Security Check
                if user_context:
                    # Normalize role to lowercase for robust comparison
                    role = str(user_context.get("role", "")).lower().strip()
                    # Handle edge case: "UserRole.ADMIN" -> "admin"
                    if "." in role:
                        role = role.split(".")[-1]
                    
                    uid = user_context.get("id")
                    
                    logger.info(f"[CHAT] RBAC Check - User Role: '{role}', Chatbot ID: {chatbot_id}")
                    
                    # Admin Bypass - admin has access to ALL chatbots
                    if role != "admin":
                        # Normalize allowed_roles to lowercase
                        raw_allowed = chatbot.get("allowed_roles", [])
                        allowed_roles = [str(r).lower().strip() for r in raw_allowed]
                        
                        logger.info(f"[CHAT] Allowed Roles: {allowed_roles}")
                        
                        if role not in allowed_roles:
                            # Check user specific (if implemented)
                            logger.warning(f"[CHAT] Access Denied. User Role: '{role}', Allowed: {allowed_roles}, Chatbot: {chatbot.get('name')}")
                            raise PermissionError(f"Bạn không có quyền truy cập Chatbot '{chatbot.get('name', 'này')}'.")
                    else:
                        logger.info(f"[CHAT] Admin access granted - bypassing role check")

                # 🔒 STRICT CONTEXT LOCKING - CRITICAL SECURITY
                # ALWAYS override client-provided dataset_ids with chatbot's linked datasets
                # This prevents users from injecting unauthorized datasets
                if "dataset_ids" in chatbot:
                    chatbot_datasets = chatbot["dataset_ids"]
                    if chatbot_datasets is None:
                        # None = use client provided (backward compatibility)
                        logger.warning(f"[CHAT] Chatbot has NO dataset restriction (dataset_ids=None)")
                    else:
                        # Empty array [] or non-empty array → ENFORCE LOCK
                        logger.info(f"[CHAT] Context Locking ENFORCED: Chatbot datasets={chatbot_datasets}")
                        dataset_ids = chatbot_datasets  # Override even if empty!
                        
                        if not dataset_ids:
                            # Empty datasets = chatbot has NO knowledge base
                            logger.warning(f"[CHAT] Chatbot '{chatbot.get('name')}' has ZERO datasets configured!")
                else:
                    # No dataset_ids field = unrestricted (old chatbots)
                    logger.warning(f"[CHAT] Chatbot missing 'dataset_ids' field - no restriction applied")
                
                if "config" in chatbot:
                    cfg = chatbot["config"]
                    rag_top_k = cfg.get("top_k", rag_top_k) or DEFAULT_TOP_K
                    rag_reranker = cfg.get("reranker")
                    rag_threshold = cfg.get("similarity_threshold", rag_threshold)
                    rag_api_key = cfg.get("api_key") # Extract API Key
                    rag_api_base_url = cfg.get("api_base_url")  # Per-bot provider endpoint
                    rag_model = cfg.get("model")     # Extract Model
                    rag_system_prompt = cfg.get("system_prompt") # Extract Prompt
                    rag_temperature = cfg.get("temperature", 0.7)
                    rag_max_tokens = cfg.get("max_tokens", 2048)
                    
                    enable_query_reformulation = bool(cfg.get("enable_query_reformulation", False))
                    enable_history_compression = bool(cfg.get("enable_history_compression", False))
                    rag_search_mode = str(cfg.get("search_mode") or "hybrid").lower()
                    if rag_search_mode not in {"hybrid", "vector", "keyword"}:
                        rag_search_mode = "hybrid"
                    history_limit = cfg.get("history_limit", 3)
                    buffer_limit = cfg.get("buffer_limit", 2)
                    compression_model = cfg.get("compression_model", "gemini-1.5-flash")
                    debug_metrics["search_mode"] = rag_search_mode
                    debug_metrics["similarity_threshold"] = rag_threshold
                    
                    # Update debug metrics with config info
                    debug_metrics["model_used"] = rag_model
                    debug_metrics["reranker_used"] = rag_reranker

                
        # 2.5 Query Reformulation (Viết lại truy vấn dựa trên lịch sử để tăng độ chính xác)
        search_query = question
        search_embedding = q_embedding
        
        if (
            enable_query_reformulation
            and not settings.chat_fast_path
            and history
            and len(history) >= 3
        ):
            # Bỏ tin nhắn user vừa gửi ở cuối cùng để lấy lịch sử hội thoại trước đó
            past_history = history[:-1]
            reformulation_prompt = prompt_service.build_reformulation_prompt(past_history, question)
            try:
                logger.info(f"[CHAT] Đang viết lại truy vấn bằng model={compression_model}...")
                rewritten_query = await self._generate_answer(
                    prompt=reformulation_prompt,
                    api_key=rag_api_key,
                    model_name=compression_model,
                    temperature=0.0,
                    base_url=rag_api_base_url,
                    max_tokens=128,
                    timeout=8.0,
                )
                rewritten_query = rewritten_query.strip()
                if rewritten_query and is_cacheable_answer(rewritten_query):
                    search_query = rewritten_query
                    logger.info(f"[CHAT] Đã viết lại câu hỏi: '{question}' -> '{search_query}'")
                    # Tiến hành embed lại câu hỏi đã viết lại để tìm kiếm vector chính xác hơn
                    start_reembed = time.time()
                    new_embed = self._try_embed_question(search_query)
                    if new_embed is not None:
                        search_embedding = new_embed
                        logger.info(f"[CHAT] Đã embed lại truy vấn mới trong {round((time.time() - start_reembed) * 1000, 2)}ms")
            except Exception as ref_err:
                logger.error(f"[CHAT] Query reformulation failed: {ref_err}")

        grouped_results = []
        errors = []
        
        # 3. Retrieval Process with timing
        start_retrieval = time.time()
        
        if dataset_ids:
            # Has dataset_ids to search
            for ds_id in dataset_ids:
                res = await self._search_dataset(
                    ds_id, 
                    search_query,
                    search_embedding,
                    top_k=rag_top_k,
                    search_mode=rag_search_mode,
                )
                grouped_results.append(res)
                if res.get("error"):
                    errors.append({"dataset_id": ds_id, "error": res["error"]})
        else:
            # No datasets configured
            if chatbot_id and self.chatbot_repo:
                # Chatbot explicitly has NO datasets = No knowledge base
                logger.warning(f"[CHAT] Chatbot '{chatbot.get('name', chatbot_id)}' has ZERO datasets - cannot answer from documents")
                # grouped_results stays empty, LLM prompt will handle "no knowledge" case
            else:
                # Legacy: No chatbot_id provided, list all datasets (backward compatibility)
                logger.warning(f"[CHAT] No chatbot context - listing all datasets (legacy mode)")
                await self._list_all_datasets_context(grouped_results)

        debug_metrics["retrieval_time_ms"] = round((time.time() - start_retrieval) * 1000, 2)
        debug_metrics["datasets_searched"] = len(dataset_ids)

        # 4. Reranking Process (Sắp xếp lại kết quả) with timing
        start_rerank = time.time()
        if settings.chat_fast_path:
            logger.info("[CHAT] fast_path: skip rerank")
            debug_metrics["reranker_used"] = None
        elif rag_reranker and rag_reranker != "None":
            self._apply_reranking(search_query, grouped_results, reranker_model=rag_reranker)
        debug_metrics["rerank_time_ms"] = round((time.time() - start_rerank) * 1000, 2)
        apply_score_threshold(grouped_results, rag_threshold)

        # 4.3 Parent-Child Retrieval: Thay thế child chunks bằng parent chunks để gửi làm context cho LLM
        parent_chunk_ids = set()
        for g in grouped_results:
            for r in g.get("results", []):
                pid = r.get("parent_chunk_id")
                if pid:
                    parent_chunk_ids.add(pid)
                    
        if parent_chunk_ids:
            try:
                logger.info(f"[CHAT] Đang lấy nội dung cho {len(parent_chunk_ids)} Parent chunks từ MongoDB...")
                parent_docs = await self.chunk_repo.get_parent_chunks_by_ids(list(parent_chunk_ids))
                parent_map = {str(doc["id"]): doc for doc in parent_docs}
                
                replaced_count = 0
                for g in grouped_results:
                    for r in g.get("results", []):
                        pid = r.get("parent_chunk_id")
                        if pid and pid in parent_map:
                            r["child_text"] = r["text"]  # Lưu lại child text thô
                            r["text"] = parent_map[pid].get("text")  # Ghi đè bằng parent text
                            replaced_count += 1
                logger.info(f"[CHAT] Đã thay thế thành công {replaced_count} child chunks bằng parent chunks.")
            except Exception as pe_err:
                logger.error(f"[CHAT] Lỗi khi mapping parent chunks: {str(pe_err)}")

        # 4.5 ✅ NO CONTEXT BEHAVIOR - Xử lý khi không tìm thấy tài liệu
        # Đếm số chunks thực sự tìm được và calculate metrics
        all_chunks = []
        for g in grouped_results:
            all_chunks.extend(g.get("results", []))
        
        total_chunks = len(all_chunks)
        debug_metrics["chunks_found"] = total_chunks
        debug_metrics["chunks_after_rerank"] = total_chunks
        
        # Calculate similarity scores
        if all_chunks:
            scores = [c.get("score", 0) for c in all_chunks if c.get("score")]
            if scores:
                debug_metrics["avg_similarity_score"] = round(sum(scores) / len(scores), 4)
                debug_metrics["top_similarity_score"] = round(max(scores), 4)
        
        # Lấy cấu hình no_context từ chatbot config
        no_context_behavior = "reject"  # Default: từ chối
        no_context_custom_msg = None
        
        if chatbot_id and self.chatbot_repo and chatbot:
            cfg = chatbot.get("config", {})
            no_context_behavior = cfg.get("no_context_behavior", "reject")
            no_context_custom_msg = cfg.get("no_context_message")
        
        if total_chunks == 0:
            logger.warning(f"[CHAT] No context found - Behavior: {no_context_behavior}")
            debug_metrics["no_context"] = True
            
            if no_context_behavior == "reject":
                # ❌ REJECT: Không gọi LLM, trả về thông báo từ chối
                no_context_answer = (
                    "Xin lỗi, tôi không tìm thấy thông tin liên quan đến câu hỏi của bạn trong tài liệu. "
                )
            elif no_context_behavior == "custom_message":
                # 📝 CUSTOM MESSAGE: Trả về thông báo tùy chỉnh
                no_context_answer = no_context_custom_msg or "Xin lỗi, tôi không tìm thấy thông tin phù hợp trong tài liệu."
            elif no_context_behavior == "fallback_llm":
                # 🤖 FALLBACK LLM: Vẫn gọi LLM nhưng cảnh báo không có context
                logger.info(f"[CHAT] Fallback to LLM without context (configured behavior)")
                # Tiếp tục flow bình thường, LLM sẽ trả lời từ kiến thức chung
                pass  # Skip to step 5
            else:
                # Unknown behavior -> default reject
                no_context_answer = "Xin lỗi, tôi không tìm thấy thông tin liên quan trong tài liệu."
            
            # Nếu không phải fallback_llm thì return ngay
            if no_context_behavior != "fallback_llm":
                assistant_message_id = None
                if session_id and self.session_repo:
                    saved = await self.session_repo.add_message(
                        session_id, "assistant", no_context_answer,
                        extra={"no_context": True},
                    )
                    assistant_message_id = saved.get("id")
                if stream_callback:
                    await stream_callback(no_context_answer)
                
                debug_metrics["total_time_ms"] = round((time.time() - start_total) * 1000, 2)
                return self._format_response(
                    question, 
                    no_context_answer, 
                    grouped_results, 
                    errors, 
                    cached=False,
                    no_context=True,
                    debug_metrics=debug_metrics,
                    message_id=assistant_message_id,
                )

        # 4.7 History Compression (Nén lịch sử hội thoại nếu vượt quá ngưỡng đệm tích lũy)
        history_for_prompt = history[:-1] if history else []
        
        if (
            enable_history_compression
            and not settings.chat_fast_path
            and session_id
            and history
            and (len(history) - 1) > 2 * (history_limit + buffer_limit)
        ):
            num_keep = 2 * history_limit
            # Tin nhắn cần nén: tất cả trừ num_keep tin nhắn gần nhất trong lịch sử cũ
            messages_to_compress = history[:-1][:-num_keep]
            raw_history_to_keep = history[:-1][-num_keep:]
            
            if messages_to_compress:
                compression_prompt = prompt_service.build_compression_prompt(
                    old_summary=conversation_summary,
                    messages_to_compress=messages_to_compress
                )
                try:
                    logger.info(f"[CHAT] Đang nén {len(messages_to_compress)} tin nhắn cũ trong session {session_id} với model={compression_model}...")
                    new_summary = await self._generate_answer(
                        prompt=compression_prompt,
                        api_key=rag_api_key,
                        model_name=compression_model,
                        temperature=0.3,
                        base_url=rag_api_base_url,
                        max_tokens=256,
                        timeout=8.0,
                    )
                    new_summary = new_summary.strip()
                    if new_summary and is_cacheable_answer(new_summary):
                        conversation_summary = new_summary
                        # Cập nhật vào DB
                        await self.session_repo.update_session(session_id, {"conversation_summary": conversation_summary})
                        logger.info(f"[CHAT] Đã cập nhật conversation_summary thành công cho session {session_id}")
                        history_for_prompt = raw_history_to_keep
                except Exception as comp_err:
                    logger.error(f"[CHAT] History compression failed: {comp_err}")
        
        # 5. Generation Process (Sinh câu trả lời từ LLM) - CHỈ khi có context hoặc fallback_llm
        start_llm = time.time()
        prompt = prompt_service.build_prompt(
            question=question, # Trả lời cho câu hỏi gốc của user
            grouped_results=grouped_results, 
            history=history_for_prompt, 
            system_prompt=rag_system_prompt,
            conversation_summary=conversation_summary
        )
        if stream_callback:
            parts: List[str] = []
            async for token in llm_service.generate_stream(
                prompt,
                api_key=rag_api_key,
                model_name=rag_model,
                temperature=rag_temperature,
                max_tokens=rag_max_tokens,
                base_url=rag_api_base_url,
            ):
                if token:
                    parts.append(token)
                    await stream_callback(token)
            answer = "".join(parts).strip() or "Xin lỗi, mô hình AI đã trả về câu trả lời rỗng."
        else:
            answer = await self._generate_answer(
                prompt, 
                api_key=rag_api_key, 
                model_name=rag_model,
                temperature=rag_temperature,
                max_tokens=rag_max_tokens,
                base_url=rag_api_base_url,
            )
        debug_metrics["llm_time_ms"] = round((time.time() - start_llm) * 1000, 2)

        # 6. Save Cache (with chatbot_id to isolate per-bot cache)
        if (
            settings.semantic_cache_enabled
            and q_embedding is not None
            and is_cacheable_answer(answer)
            and not errors
        ):
            semantic_cache_service.set(question, q_embedding, answer, suffix=cache_key_suffix)
            
        # Finalize debug metrics before persist so latency is stored
        debug_metrics["total_time_ms"] = round((time.time() - start_total) * 1000, 2)

        # 7. Save Bot Message to Session (keep sources for reload)
        assistant_message_id = None
        if session_id and self.session_repo:
            saved = await self.session_repo.add_message(
                session_id,
                "assistant",
                answer,
                extra={
                    "sources": grouped_results,
                    "latency_ms": debug_metrics["total_time_ms"],
                },
            )
            assistant_message_id = saved.get("id")
        
        return self._format_response(
            question, answer, grouped_results, errors, cached=False,
            debug_metrics=debug_metrics, message_id=assistant_message_id,
        )

    async def _search_dataset(
        self, 
        dataset_id: str, 
        question: str,
        q_vec: Optional[np.ndarray],
        top_k: int = DEFAULT_TOP_K,
        search_mode: str = "hybrid",
    ) -> Dict[str, Any]:
        """Tìm kiếm chunks liên quan trong một dataset cụ thể."""
        result_template = {
            "dataset_id": dataset_id,
            "dataset_name": None,
            "results": [],
            "error": None
        }
        
        try:
            # Lấy thông tin & Config dataset
            dataset = await self.dataset_repo.get_by_id(dataset_id)
            if not dataset:
                result_template["error"] = "Dataset không tồn tại"
                return result_template
            
            result_template["dataset_name"] = dataset.get("name")
            
            # Embed lại nếu model dataset khác model default (nếu cần xử lý đa model)
            # Hiện tại dùng model chung, reuse q_vec nếu có
            if q_vec is None:
                q_vec = self._try_embed_question(question)
                if q_vec is None:
                    raise ValueError("Không thể embed câu hỏi")
            
            # CRITICAL FIX: Validate embedding dimension trước khi search
            # Ngăn chặn crash khi embedding model thay đổi dimension
            # Vietnamese SBERT dimension = 768
            expected_dim = 768
            actual_dim = q_vec.shape[0] if len(q_vec.shape) == 1 else q_vec.shape[1]
            
            if actual_dim != expected_dim:
                error_msg = (
                    f"Embedding dimension mismatch: expected {expected_dim}, got {actual_dim}. "
                    f"Dataset có thể đã được index với model khác. Vui lòng re-index dataset."
                )
                logger.error(f"[CHAT] {error_msg}")
                result_template["error"] = error_msg
                return result_template

            # A. Prepare Filter: Chỉ lấy chunk từ file đang active (Enabled)
            enabled_files = await self.dataset_file_repo.get_enabled_by_dataset(dataset_id)
            if not enabled_files:
                logger.info(f"[CHAT] No enabled files in dataset {dataset_id}")
                return result_template
                
            enabled_ids = [str(f["id"]) for f in enabled_files]
            
            # Tạo mapping file_id -> file_name để enrich chunk results
            # CRITICAL FIX: dataset_file KHÔNG có field 'name', phải query File repository
            # enabled_files chỉ có: {id, dataset_id, file_id, status, is_enabled}
            # Cần lấy file_id -> query files collection -> lấy name
            file_id_to_name_map = {}
            file_ids = [str(f.get("file_id")) for f in enabled_files if f.get("file_id")]
            
            if file_ids:
                file_repo = self.file_repo
                if file_repo is None:
                    file_repo = FileRepository(self.dataset_repo.db)
                file_docs = await file_repo.get_by_ids(file_ids)
                for file_doc in file_docs:
                    file_id_to_name_map[str(file_doc.get("id"))] = file_doc.get("name", "Unnamed File")
                for file_id in file_ids:
                    file_id_to_name_map.setdefault(file_id, "Unknown File")
            
            # Inject File List info for LLM Context
            result_template["files"] = list(file_id_to_name_map.values())

            mode = (search_mode or "hybrid").lower()
            use_vector = mode in {"hybrid", "vector"}
            use_keyword = mode in {"hybrid", "keyword"}

            vector_ranked: List[tuple] = []
            if use_vector:
                try:
                    scores, payloads = vector_service.search(
                        dataset_id,
                        q_vec,
                        top_k=top_k,
                        allowed_file_ids=enabled_ids,
                    )
                    if scores:
                        for score, payload in zip(scores, payloads):
                            payload["score"] = score
                            vector_ranked.append((payload, float(score)))
                except Exception as vs_err:
                    logger.error(f"[CHAT] Vector search failed for {dataset_id}: {vs_err}")

            regex_chunks = []
            if use_keyword:
                regex_chunks = await self.chunk_repo.search_by_text(
                    query=question,
                    dataset_file_ids=enabled_ids,
                    limit=max(3, top_k),
                )

            v_chunk_map = {}
            if vector_ranked:
                v_chunk_ids = [p["chunk_id"] for p, _ in vector_ranked]
                v_chunks_db = await self.chunk_repo.get_by_ids(v_chunk_ids)
                v_chunk_map = {str(c["id"]): c for c in v_chunks_db}

            vector_items = []
            for payload, score in vector_ranked:
                cdata = v_chunk_map.get(payload["chunk_id"])
                if cdata:
                    vector_items.append((cdata, score, "vector"))
            keyword_items = [(chunk, None, "keyword") for chunk in regex_chunks]

            if mode == "hybrid" and vector_items and keyword_items:
                merged = rrf_merge(vector_items, keyword_items)
            elif mode == "keyword":
                merged = [
                    (chunk, 1.0 / (60 + i + 1), "keyword", None)
                    for i, (chunk, _, _) in enumerate(keyword_items)
                ]
            else:
                merged = [(chunk, score, origin, score) for chunk, score, origin in vector_items]

            final_results = []
            seen_chunk_ids = set()
            for row in merged:
                chunk_data, score, origin = row[0], row[1], row[2]
                raw_score = row[3] if len(row) > 3 else (score if origin == "vector" else None)
                cid = str(chunk_data.get("_id") or chunk_data.get("id"))
                if cid in seen_chunk_ids:
                    continue
                seen_chunk_ids.add(cid)
                file_id = str(chunk_data.get("file_id"))
                file_name = file_id_to_name_map.get(file_id, "Unknown File")
                cite_ref = f"[{dataset_id}:{file_id}:{chunk_data.get('chunk_index')}]"
                vector_score = float(raw_score) if origin == "vector" and raw_score is not None else None
                final_results.append({
                    "vector_id": cid,
                    "score": float(score or 0),
                    "vector_score": vector_score,
                    "text": chunk_data.get("text"),
                    "embedding_text": chunk_data.get("embedding_text") or chunk_data.get("context_enriched_text"),
                    "file_id": file_id,
                    "file_name": file_name,
                    "dataset_file_id": chunk_data.get("dataset_file_id"),
                    "chunk_index": chunk_data.get("chunk_index"),
                    "parent_chunk_id": chunk_data.get("parent_chunk_id"),
                    "cite": cite_ref,
                    "origin": origin,
                    "page": chunk_data.get("page") or chunk_data.get("page_number"),
                })
            
            if not final_results:
                logger.info(f"[CHAT] No results (Vector+Regex) for dataset {dataset_id}")
                return result_template
                
            result_template["results"] = final_results
            return result_template

        except Exception as e:
            logger.error(f"[CHAT] Search Error dataset={dataset_id}: {e}")
            result_template["error"] = str(e)
            return result_template

    def _try_embed_question(self, question: str) -> Optional[np.ndarray]:
        """Thử embed câu hỏi, log warning nếu lỗi."""
        try:
            vecs = embedding_service.embed_texts([question])
            return vecs[0] if len(vecs) > 0 else None
        except Exception as e:
            logger.error(f"[CHAT] Embed error: {e}")
            return None

    async def _list_all_datasets_context(self, grouped_results: List[Dict]):
        """Helper để list toàn bộ dataset nếu user không chọn cụ thể."""
        all_datasets = await self.dataset_repo.get_all()
        for d in all_datasets:
            grouped_results.append({
                "dataset_id": d["id"],
                "dataset_name": d.get("name"),
                "results": []
            })

    def _apply_reranking(
        self, 
        question: str, 
        grouped_results: List[Dict],
        reranker_model: Optional[str] = None
    ):
        """
        Áp dụng Rerank logic dựa trên config chatbot.
        
        Supported models:
        - None: Không rerank, giữ nguyên thứ tự vector similarity
        - ms-marco-MiniLM-L-6-v2: Nhanh nhất (~100-200ms)
        - ms-marco-MiniLM-L-12-v2: Cân bằng (~200-400ms) 
        - bge-reranker-v2-m3: Chính xác nhất (~2-8s)
        - Semantic/CrossEncoder: Legacy aliases
        """
        # Skip reranking if disabled
        if not reranker_model or reranker_model.lower() == "none":
            logger.info("[CHAT] Reranking disabled - using vector similarity order")
            return
        
        # Map legacy values to new model names
        model_mapping = {
            "semantic": "ms-marco-MiniLM-L-6-v2",
            "crossencoder": "bge-reranker-v2-m3",
        }
        
        actual_model = model_mapping.get(reranker_model.lower(), reranker_model)
        
        try:
            for group in grouped_results:
                results = group.get("results", [])
                if not results:
                    continue
                
                logger.info(f"[CHAT] Reranking {len(results)} chunks with model={actual_model}")
                reranked = rerank_service.rerank(question, results, model_name=actual_model)
                group["results"] = reranked
        except Exception as e:
            logger.warning(f"[CHAT] Rerank warning: {e}")

    async def _generate_answer(
        self, 
        prompt: str, 
        api_key: Optional[str] = None, 
        model_name: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> str:
        """Gọi LLM sinh câu trả lời, handle lỗi."""
        try:
            return await llm_service.generate(
                prompt, 
                api_key=api_key, 
                model_name=model_name,
                temperature=temperature,
                max_tokens=max_tokens,
                base_url=base_url,
                timeout=timeout,
            )
        except Exception as e:
            logger.exception(f"[CHAT] LLM Generation Error: {e}")
            return "Xin lỗi, hệ thống AI đang gặp sự cố. Vui lòng thử lại sau."

    def _format_response(
        self, 
        question: str, 
        answer: str, 
        sources: List[Dict], 
        errors: List[Dict],
        cached: bool,
        no_context: bool = False,
        debug_metrics: Optional[Dict[str, Any]] = None,
        message_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Format JSON trả về cho Clients."""
        return {
            "question": question,
            "answer": answer,
            "sources": sources,
            "errors": errors,
            "cached": cached,
            "no_context": no_context,  # Flag cho frontend biết không có context RAG
            "debug": debug_metrics,  # Debug metrics for performance analysis
            "message_id": message_id,
        }
