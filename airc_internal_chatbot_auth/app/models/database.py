"""
Database Collections - Constants cho MongoDB collections
"""
from enum import Enum


class Collections(str, Enum):
    """MongoDB collections"""
    USERS = "users"
