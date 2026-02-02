import logging
import sys
from rq import Worker, Queue
from app.core.queues import redis_conn

# Initialize Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

from app.services.embedding_service import embedding_service
embedding_service.preload_models()

if __name__ == "__main__":
    logger.info("Starting RAG Worker...")
    
    # Explicitly pass connection to Queue and Worker
    # 'Connection' context manager is deprecated/removed in newer RQ
    queues = [Queue("ingest", connection=redis_conn)]
    
    worker = Worker(
        queues, 
        connection=redis_conn
    )
    worker.work()
