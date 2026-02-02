import asyncio
from app.core.database import connect_to_mongo, close_mongo_connection
from app.repositories import DatasetFileRepository, FileRepository, ChunkRepository
from app.services.processing_service import ProcessingService
import logging

logger = logging.getLogger(__name__)

async def _async_process(dataset_id: str, dataset_file_id: str):
    """
    Async wrapper to initialize DB and Service, then run processing
    """
    try:
        # Connect and get Client
        await connect_to_mongo()
        
        # Access the global mongodb instance
        from app.core.database import mongodb
        from app.core.config import settings
        
        # Ensure we have a valid db reference. 
        if not mongodb.client:
             raise Exception("MongoDB client not initialized")
             
        database = mongodb.client[settings.mongodb_db_name]
        
        # Initialize Repositories with DB instance
        dataset_file_repo = DatasetFileRepository(database)
        file_repo = FileRepository(database)
        chunk_repo = ChunkRepository(database)
        
        # Initialize Service
        service = ProcessingService(
            dataset_file_repo=dataset_file_repo,
            file_repo=file_repo,
            chunk_repo=chunk_repo
        )
        
        await service.process_dataset_file(dataset_id, dataset_file_id)
        
    except Exception as e:
        logger.exception(f"Job Failed for dataset_file={dataset_file_id}: {e}")
        raise e
    finally:
        await close_mongo_connection()

def process_dataset_file_job(dataset_id: str, dataset_file_id: str):
    """
    Sync entrypoint for RQ Worker
    """
    asyncio.run(_async_process(dataset_id, dataset_file_id))
