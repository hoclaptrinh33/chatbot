"""
Statistics API endpoints
Provides dashboard statistics and system metrics
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import logging
from datetime import datetime, timedelta

from app.core import get_database
from app.services.cache_service import semantic_cache_service

logger = logging.getLogger(__name__)

router = APIRouter()


class DashboardStats(BaseModel):
    """Dashboard statistics response"""
    chatbot_count: int = 0
    dataset_count: int = 0
    conversation_count: int = 0
    user_count: int = 0
    
    # RAG Performance
    avg_response_time: float = 0.0  # seconds
    accuracy_rate: float = 0.0  # percentage
    cache_hit_rate: float = 0.0  # percentage
    total_chunks_indexed: int = 0
    
    # Recent activity
    conversations_today: int = 0
    datasets_processing: int = 0


class RecentActivity(BaseModel):
    """Recent activity item"""
    type: str  # chatbot, dataset, conversation
    title: str
    description: str
    timestamp: datetime


@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard_stats():
    """
    Get dashboard statistics for admin view
    """
    try:
        db = await get_database()
        
        # Count collections
        chatbot_count = await db.chatbots.count_documents({})
        dataset_count = await db.datasets.count_documents({})
        conversation_count = await db.conversations.count_documents({})
        
        # Count users from auth service (if available) - for now count from conversations
        # Get unique user_ids from conversations
        user_ids = await db.conversations.distinct("user_id")
        user_count = len(user_ids) if user_ids else 0
        
        # Count chunks in qdrant (approximate from datasets)
        total_chunks = 0
        datasets = await db.datasets.find({}, {"chunk_count": 1}).to_list(None)
        for ds in datasets:
            total_chunks += ds.get("chunk_count", 0)
        
        # Count datasets being processed
        datasets_processing = await db.datasets.count_documents({
            "status": {"$in": ["processing", "pending"]}
        })
        
        # Count conversations today
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        conversations_today = await db.conversations.count_documents({
            "created_at": {"$gte": today_start}
        })
        
        # Get cache stats
        cache_stats = semantic_cache_service.get_stats()
        cache_hit_rate = 0.0
        if cache_stats.get("hits", 0) + cache_stats.get("misses", 0) > 0:
            cache_hit_rate = (cache_stats.get("hits", 0) / 
                           (cache_stats.get("hits", 0) + cache_stats.get("misses", 0))) * 100
        
        # Calculate average response time from recent conversations
        # For now use a reasonable default - can be enhanced with actual metrics
        avg_response_time = 1.2  # Default 1.2s
        
        # Accuracy rate - can be calculated from feedback if implemented
        accuracy_rate = 89.0  # Default - TODO: implement feedback-based calculation
        
        return DashboardStats(
            chatbot_count=chatbot_count,
            dataset_count=dataset_count,
            conversation_count=conversation_count,
            user_count=user_count,
            avg_response_time=avg_response_time,
            accuracy_rate=accuracy_rate,
            cache_hit_rate=round(cache_hit_rate, 1),
            total_chunks_indexed=total_chunks,
            conversations_today=conversations_today,
            datasets_processing=datasets_processing
        )
        
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recent-activity", response_model=List[RecentActivity])
async def get_recent_activity(limit: int = 5):
    """
    Get recent system activities for dashboard
    """
    try:
        db = await get_database()
        activities = []
        
        # Get recent chatbot updates
        chatbots = await db.chatbots.find({}).sort("updated_at", -1).limit(2).to_list(None)
        for bot in chatbots:
            activities.append(RecentActivity(
                type="chatbot",
                title=f'Chatbot "{bot.get("name", "Unknown")}"',
                description="được cập nhật",
                timestamp=bot.get("updated_at", datetime.utcnow())
            ))
        
        # Get recent dataset processing
        datasets = await db.datasets.find({
            "status": "completed"
        }).sort("updated_at", -1).limit(2).to_list(None)
        for ds in datasets:
            activities.append(RecentActivity(
                type="dataset",
                title=f'Dataset "{ds.get("name", "Unknown")}"',
                description="xử lý hoàn tất",
                timestamp=ds.get("updated_at", datetime.utcnow())
            ))
        
        # Get today's conversation count
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        conv_today = await db.conversations.count_documents({
            "created_at": {"$gte": today_start}
        })
        if conv_today > 0:
            activities.append(RecentActivity(
                type="conversation",
                title=f"{conv_today} cuộc hội thoại mới",
                description="trong hôm nay",
                timestamp=datetime.utcnow()
            ))
        
        # Sort by timestamp desc and limit
        activities.sort(key=lambda x: x.timestamp, reverse=True)
        return activities[:limit]
        
    except Exception as e:
        logger.error(f"Error getting recent activity: {e}")
        raise HTTPException(status_code=500, detail=str(e))
