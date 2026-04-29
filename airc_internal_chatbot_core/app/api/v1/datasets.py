"""
Dataset Controller - API endpoints cho dataset management
"""
from fastapi import APIRouter, Depends, HTTPException
from app.models.schemas import (
    DatasetCreate,
    DatasetResponse,
    AddFilesToDatasetRequest,
    DatasetFileResponse,
    ToggleDatasetFileRequest,
    ShareDatasetRequest,
    SuccessResponse,
    ChunkResponse
)
from app.services import DatasetService
from app.api.dependencies import get_dataset_service, get_current_user
from typing import List
import logging
from app.models.auth import User

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/ping")
async def ping_dataset():
    return {"message": "pong"}

@router.post("", response_model=DatasetResponse, status_code=201)
async def create_dataset(
    payload: DatasetCreate,
    current_user: User = Depends(get_current_user),
    dataset_service: DatasetService = Depends(get_dataset_service)
):
    """Tạo dataset mới (Employee/Admin only)"""
    try:
        # Check permission
        user_role = current_user.role
        if user_role not in ["admin", "employee"]:
            raise HTTPException(status_code=403, detail="Permission denied")
        
        # Config logic removed
        # config = { ... }
        
        dataset = await dataset_service.create_dataset(
            name=payload.name, 
            # config=config, # Removed
            owner_id=current_user.user_id,
            visibility=payload.visibility,
            chatbot_ids=payload.chatbot_ids  # ✅ Pass chatbot_ids for assignment
        )
        return DatasetResponse(**dataset)
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error creating dataset")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=List[DatasetResponse])
async def list_datasets(
    current_user: User = Depends(get_current_user),
    dataset_service: DatasetService = Depends(get_dataset_service)
):
    """Lấy danh sách datasets (filtered by role)"""
    try:
        user_role = current_user.role
        user_id = current_user.user_id
        
        if user_role == "admin":
            # Admin sees all datasets
            datasets = await dataset_service.list_datasets()
        elif user_role == "employee":
            # Employee sees own datasets
            datasets = await dataset_service.list_datasets_by_owner(user_id)
        else:  # intern_guest
            # Intern/Guest sees shared datasets only
            datasets = await dataset_service.list_datasets_shared_with(user_id)
        
        return [DatasetResponse(**ds) for ds in datasets]
    except Exception as e:
        logger.exception("Error listing datasets")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{dataset_id}", response_model=DatasetResponse)
async def get_dataset(
    dataset_id: str,
    dataset_service: DatasetService = Depends(get_dataset_service)
):
    """Lấy dataset theo ID"""
    dataset = await dataset_service.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return DatasetResponse(**dataset)


@router.patch("/{dataset_id}", response_model=DatasetResponse)
async def update_dataset(
    dataset_id: str,
    payload: DatasetCreate, # Reuse create schema for update (mostly same fields) or create new Update schema? Let's use payload.dict(exclude_unset=True)
    current_user: User = Depends(get_current_user),
    dataset_service: DatasetService = Depends(get_dataset_service)
):
    """
    Update dataset (config, name)
    Permission: Admin OR Owner
    """
    dataset = await dataset_service.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    user_role = current_user.role
    user_id = current_user.user_id
    
    # Check permission
    is_admin = user_role == "admin"
    is_owner = dataset.get("owner_id") == user_id
    
    if not (is_admin or is_owner):
        raise HTTPException(status_code=403, detail="Permission denied")

    # Construct update data
    update_data = {
        "name": payload.name,
        # Config removed
        "visibility": payload.visibility
    }
    
    # Use service to update
    updated = await dataset_service.update_dataset(dataset_id, update_data)
    if not updated:
         raise HTTPException(status_code=500, detail="Failed to update dataset")
         
    return DatasetResponse(**updated)


@router.delete("/{dataset_id}", response_model=SuccessResponse)
async def delete_dataset(
    dataset_id: str,
    current_user: User = Depends(get_current_user),
    dataset_service: DatasetService = Depends(get_dataset_service)
):
    """
    Xóa dataset
    Permission: Admin (any dataset) OR Owner (own dataset)
    """
    # Get dataset to check ownership
    dataset = await dataset_service.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    user_role = current_user.role
    user_id = current_user.user_id
    
    # Check permission
    is_admin = user_role == "admin"
    is_owner = dataset.get("owner_id") == user_id
    
    if not (is_admin or is_owner):
        raise HTTPException(
            status_code=403,
            detail="Permission denied: Only admin or dataset owner can delete"
        )
    
    success = await dataset_service.delete_dataset(dataset_id)
    if not success:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return SuccessResponse(status="success", message="Dataset deleted")


from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from app.services import DatasetService
from app.api.dependencies import get_dataset_service, get_current_user, get_processing_service
from app.services.processing_service import ProcessingService

# ... (existing imports)

@router.post("/{dataset_id}/files")
async def add_files_to_dataset(
    dataset_id: str,
    payload: AddFilesToDatasetRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    dataset_service: DatasetService = Depends(get_dataset_service),
    processing_service: ProcessingService = Depends(get_processing_service)
):
    """
    Thêm files vào dataset
    Permission: Admin/Employee only, must be owner (employee) or admin
    """
    user_role = current_user.role
    user_id = current_user.user_id
    
    # Check role: Only admin/employee can add files
    if user_role not in ["admin", "employee"]:
        raise HTTPException(
            status_code=403,
            detail="Permission denied: Only admin/employee can add files"
        )
    
    # Check ownership for employees
    if user_role == "employee":
        dataset = await dataset_service.get_dataset(dataset_id)
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found")
        
        if dataset.get("owner_id") != user_id:
            raise HTTPException(
                status_code=403,
                detail="Permission denied: Not dataset owner"
            )
    
    try:
        result = await dataset_service.add_files_to_dataset(
            dataset_id, 
            payload.file_ids
        )
        
        # Trigger background processing for added files
        from app.core.queues import ingest_queue
        from app.jobs.ingest import process_dataset_file_job
        
        for df in result["added"]:
            ingest_queue.enqueue(
                process_dataset_file_job,
                dataset_id,
                str(df["id"]),
                job_timeout='1h' # Long timeout for big files
            )
            
        return {
            "status": "success",
            "added": result["added"],
            "skipped": result["skipped"]
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error adding files to dataset")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{dataset_id}/files", response_model=List[DatasetFileResponse])
async def list_dataset_files(
    dataset_id: str,
    dataset_service: DatasetService = Depends(get_dataset_service)
):
    """Lấy danh sách files trong dataset"""
    files = await dataset_service.get_dataset_files(dataset_id)
    return [DatasetFileResponse(**f) for f in files]


@router.patch("/{dataset_id}/files/{dataset_file_id}", response_model=SuccessResponse)
async def toggle_dataset_file(
    dataset_id: str,
    dataset_file_id: str,
    payload: ToggleDatasetFileRequest,
    dataset_service: DatasetService = Depends(get_dataset_service)
):
    """Bật/tắt file trong dataset"""
    success = await dataset_service.toggle_dataset_file(
        dataset_file_id,
        payload.is_enabled
    )
    if not success:
        raise HTTPException(status_code=400, detail="Update failed")
    return SuccessResponse(status="success")


@router.delete("/{dataset_id}/files/{dataset_file_id}", response_model=SuccessResponse)
async def remove_dataset_file(
    dataset_id: str,
    dataset_file_id: str,
    current_user: User = Depends(get_current_user),
    dataset_service: DatasetService = Depends(get_dataset_service)
):
    """
    Xóa file khỏi dataset
    Permission: Admin OR dataset owner
    """
    user_role = current_user.role
    user_id = current_user.user_id
    
    # Check ownership for employees
    if user_role == "employee":
        dataset = await dataset_service.get_dataset(dataset_id)
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found")
        
        if dataset.get("owner_id") != user_id:
            raise HTTPException(
                status_code=403,
                detail="Permission denied: Not dataset owner"
            )
    
    success = await dataset_service.remove_file_from_dataset(
        dataset_id,
        dataset_file_id
    )
    if not success:
        raise HTTPException(status_code=400, detail="Delete failed")
    return SuccessResponse(status="success")


@router.get(
    "/{dataset_id}/files/{dataset_file_id}/chunks",
    response_model=List[ChunkResponse]
)
async def list_chunks(
    dataset_id: str,
    dataset_file_id: str,
    dataset_service: DatasetService = Depends(get_dataset_service)
):
    """Lấy danh sách chunks của dataset file"""
    try:
        logger.info(f"Listing chunks for file: {dataset_file_id} in dataset: {dataset_id}")
        chunks = await dataset_service.get_chunks(dataset_id, dataset_file_id)
        logger.info(f"Found {len(chunks)} chunks")
        return [ChunkResponse(**c) for c in chunks]
    except Exception as e:
        logger.exception("Error listing chunks")
        raise HTTPException(status_code=500, detail=str(e))


@router.put(
    "/{dataset_id}/files/{dataset_file_id}/toggle",
    response_model=SuccessResponse
)
async def toggle_dataset_file(
    dataset_id: str,
    dataset_file_id: str,
    request: ToggleDatasetFileRequest,
    dataset_service: DatasetService = Depends(get_dataset_service)
):
    """Bật/tắt trạng thái file trong dataset"""
    success = await dataset_service.toggle_file_status(dataset_id, dataset_file_id, request.enabled)
    
    if not success:
         raise HTTPException(status_code=400, detail="Update failed")
         
    return SuccessResponse(
        status="success",
        message=f"File {'enabled' if request.enabled else 'disabled'}"
    )


@router.post("/{dataset_id}/share", response_model=SuccessResponse)
async def share_dataset(
    dataset_id: str,
    payload: ShareDatasetRequest,
    current_user: User = Depends(get_current_user),
    dataset_service: DatasetService = Depends(get_dataset_service)
):
    """
    Share dataset with users (Employee/Admin only)
    
    Body:
        - user_ids: List[str] - List of target user IDs (recommended)
        - student_ids: List[str] - Legacy field for compatibility
        - all_students: bool - Legacy mode (not fully implemented)
    """
    try:
        # Check permission
        user_role = current_user.role
        if user_role not in ["admin", "employee"]:
            raise HTTPException(status_code=403, detail="Permission denied")
        
        # Verify ownership (employee) or admin
        dataset = await dataset_service.get_dataset(dataset_id)
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found")
        
        if user_role == "employee" and dataset.get("owner_id") != current_user.user_id:
            raise HTTPException(status_code=403, detail="Not your dataset")

        has_explicit_user_list = payload.user_ids is not None or payload.student_ids is not None

        if payload.user_ids is not None:
            target_user_ids = payload.user_ids
        elif payload.student_ids is not None:
            target_user_ids = payload.student_ids
        elif payload.all_students:
            target_user_ids = []
            logger.warning("Share with all_students mode is not fully implemented yet")
        else:
            raise HTTPException(status_code=400, detail="Missing required field: user_ids")

        # Normalize IDs: strip empty values and deduplicate while preserving order.
        normalized_user_ids = list(dict.fromkeys([
            uid.strip() for uid in target_user_ids if isinstance(uid, str) and uid.strip()
        ]))

        # If caller explicitly provides empty list, treat as unshare-all.
        if not payload.all_students and not has_explicit_user_list:
            raise HTTPException(status_code=400, detail="Missing required field: user_ids")
        
        # Share dataset
        success = await dataset_service.share_dataset(dataset_id, normalized_user_ids)
        if not success:
            raise HTTPException(status_code=400, detail="Failed to share dataset")
        
        return SuccessResponse(
            status="success",
            message=(
                f"Dataset shared with {len(normalized_user_ids)} users"
                if not payload.all_students
                else "Dataset share updated (all_students mode pending full implementation)"
            )
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error sharing dataset")
        raise HTTPException(status_code=500, detail=str(e))
