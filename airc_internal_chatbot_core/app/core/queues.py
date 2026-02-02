from redis import Redis
from rq import Queue
from app.core.config import settings
import os

# Parse Redis URL or use Env directly
# settings.redis_url should be like "redis://redis:6379/0"
redis_conn = Redis.from_url(settings.redis_url)

# Define Queues
# 'default' can be used, or named queues like 'ingest'
ingest_queue = Queue("ingest", connection=redis_conn)
