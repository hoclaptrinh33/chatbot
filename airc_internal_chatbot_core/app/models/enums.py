"""
Enums - Định nghĩa các enum types
"""
from enum import Enum


class FileStatus(str, Enum):
    """Trạng thái file"""
    PENDING = "Pending"
    PROCESSING = "Processing"
    READY = "Ready"
    ERROR = "Error"


class DatasetFileStatus(str, Enum):
    """Trạng thái dataset file"""
    PENDING = "pending"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    DONE = "done"
    ERROR = "error"
