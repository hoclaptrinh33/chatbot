"""
File Controller - API endpoints cho file upload/management
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse as StreamFileResponse, StreamingResponse
from app.models.schemas import FileUploadResponse, FileResponse
from app.repositories import FileRepository
from app.api.dependencies import get_file_repo, get_current_user
from app.models.enums import FileStatus
from typing import List
import logging
import os
import aiofiles

logger = logging.getLogger(__name__)

router = APIRouter()

# Local upload directory setup
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


from app.models.auth import User

@router.post("/upload", response_model=FileUploadResponse, status_code=201)
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    file_repo: FileRepository = Depends(get_file_repo)
):
    """
    Upload file lên Local Storage và tạo File record
    
    - **file**: Binary file (PDF, DOCX, TXT, ...)
    - Chỉ Admin/Teacher được upload
    """
    try:
        # Check permission
        user_role = current_user.role
        if user_role not in ["admin", "teacher"]:
            raise HTTPException(status_code=403, detail="Permission denied: Only admin/teacher can upload files")
        
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        
        # Read file content
        file_content = await file.read()
        file_size = len(file_content)
        
        # Check file size (max 200MB as per config.py)
        MAX_SIZE = 200 * 1024 * 1024
        if file_size > MAX_SIZE:
            raise HTTPException(status_code=400, detail=f"File too large: max {MAX_SIZE} bytes")
        
        # Generate Local path
        # Structure: /app/uploads/{user_id}/{filename}
        user_id = current_user.user_id
        upload_dir = f"uploads/{user_id}"
        os.makedirs(upload_dir, exist_ok=True)
        
        safe_filename = os.path.basename(file.filename)
        file_path = f"{upload_dir}/{safe_filename}"
        
        # Write to disk
        async with aiofiles.open(file_path, 'wb') as out_file:
            await out_file.write(file_content)
            
        logger.info(f"Saved file to disk: {file_path}")
        
        # Create File record in MongoDB
        file_doc = await file_repo.create_file(
            name=safe_filename,
            size=file_size,
            mime_type=file.content_type or "application/octet-stream",
            path=file_path, # Store relative path or absolute path? Relative is better for portability.
            status=FileStatus.READY
        )
        
        return FileUploadResponse(
            id=file_doc["id"],
            name=file_doc["name"],
            size=file_doc["size"],
            mime_type=file_doc["mime_type"],
            status=FileStatus.READY,
            uploaded_at=file_doc["uploaded_at"]
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error uploading file")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get("/", response_model=List[FileResponse])
async def list_files(
    current_user: User = Depends(get_current_user),
    file_repo: FileRepository = Depends(get_file_repo)
):
    """
    Lấy danh sách files (hiện tại: tất cả, sau có thể filter theo user)
    """
    try:
        # Legacy behavior: /files returns ALL files (Pending + Ready)
        # This matches legacy File.getList()
        files = await file_repo.get_all()
        
        # Helper to safely convert status
        def get_safe_status(status_str):
            if not status_str:
                return FileStatus.PENDING
            
            # Map common variations
            s = str(status_str).capitalize() # "pending" -> "Pending"
            try:
                return FileStatus(s)
            except ValueError:
                # Try original just in case
                try:
                    return FileStatus(status_str)
                except ValueError:
                    return FileStatus.ERROR

        # Convert status field for each file to avoid duplicate kwargs
        result = []
        for f in files:
            file_dict = dict(f)  # Copy to avoid mutation
            file_dict["status"] = get_safe_status(file_dict.get("status"))
            result.append(FileResponse(**file_dict))
        
        return result
    except Exception as e:
        logger.exception("Error listing files")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{file_id}", response_model=FileResponse)
async def get_file(
    file_id: str,
    file_repo: FileRepository = Depends(get_file_repo)
):
    """
    Lấy thông tin file
    """
    file_doc = await file_repo.get_by_id(file_id)
    if not file_doc:
        raise HTTPException(status_code=404, detail="File not found")
        
    # Safe status conversion
    status_str = file_doc.get("status")
    try:
        status = FileStatus(str(status_str).capitalize())
    except ValueError:
        try:
             status = FileStatus(status_str)
        except ValueError:
             status = FileStatus.ERROR
             
    return FileResponse(**file_doc, status=status)


@router.get("/{file_id}/view")
async def view_file_content(
    file_id: str,
    file_repo: FileRepository = Depends(get_file_repo)
    # Note: Permission check can be added here if needed
):
    """
    Xem/Download nội dung file
    """
    file_doc = await file_repo.get_by_id(file_id)
    if not file_doc:
        raise HTTPException(status_code=404, detail="File not found")
    
    file_path = file_doc.get("path")
    
    # Debug logging
    logger.info(f"Viewing file: ID={file_id}, DB_Path={file_path}, CWD={os.getcwd()}")
    
    # Check if path is absolute or relative
    if not file_path:
        raise HTTPException(status_code=404, detail="File path not found in database")
    
    # If path is relative, make it absolute from current working directory
    if not os.path.isabs(file_path):
        file_path = os.path.join(os.getcwd(), file_path)
    
    if not os.path.exists(file_path):
        logger.error(f"File not found on disk: {file_path}")
        raise HTTPException(status_code=404, detail=f"File content not found on server. Path: {file_path}")
    
    # Get mime type - use inline disposition for viewable types
    mime_type = file_doc.get("mime_type", "application/octet-stream")
    filename = file_doc.get("name", "file")
    
    # For PDF, images, text - show inline in browser
    viewable_types = [
        "application/pdf",
        "text/plain", "text/html", "text/css", "text/javascript",
        "image/png", "image/jpeg", "image/gif", "image/webp", "image/svg+xml",
        "application/json", "application/xml"
    ]
    
    # Use inline disposition for viewable files
    if any(mime_type.startswith(vt.split('/')[0]) for vt in viewable_types) or mime_type in viewable_types:
        # Return with inline disposition for browser preview
        def file_iterator():
            with open(file_path, "rb") as f:
                yield from f
        
        return StreamingResponse(
            file_iterator(),
            media_type=mime_type,
            headers={
                "Content-Disposition": f'inline; filename="{filename}"'
            }
        )
    else:
        # For other files, download as attachment
        return StreamFileResponse(
            path=file_path,
            media_type=mime_type,
            filename=filename
        )
