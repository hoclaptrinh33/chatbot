import logging
import sys
from rq import SimpleWorker, Queue
from app.core.queues import redis_conn

# Initialize Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Worker owns heavy models. API process should keep PRELOAD_MODELS=false.
import os
if os.getenv("PRELOAD_MODELS", "true").lower() in {"1", "true", "yes"}:
    from app.services.embedding_service import embedding_service
    try:
        embedding_service.preload_models()
    except Exception as exc:
        logger.warning("Worker model preload skipped: %s", exc)

if __name__ == "__main__":
    logger.info("Starting RAG Worker...")
    
    # Explicitly pass connection to Queue and Worker
    # 'Connection' context manager is deprecated/removed in newer RQ
    queues = [Queue("ingest", connection=redis_conn)]
    
    # SimpleWorker runs jobs in-process. Forked RQ workers cannot re-init CUDA
    # after preload_models() already touched the GPU in the parent process.
    worker = SimpleWorker(
        queues,
        connection=redis_conn
    )
    worker.work()
