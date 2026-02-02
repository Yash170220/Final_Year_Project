"""Ingestion API endpoints"""
import logging
import shutil
from pathlib import Path
from typing import Dict, List
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from src.common.config import settings
from src.common.database import get_db
from src.common.models import Upload, UploadStatus
from src.common.schemas import UploadResponse, UploadStatusResponse, ErrorResponse
from src.ingestion.service import IngestionService
from src.ingestion.exceptions import ParseError, UnsupportedFileTypeError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/ingest", tags=["ingestion"])


@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid file format"},
        413: {"model": ErrorResponse, "description": "File too large"},
        422: {"model": ErrorResponse, "description": "Validation error"},
        500: {"model": ErrorResponse, "description": "Server error"}
    },
    summary="Upload and ingest a file",
    description="Upload Excel or CSV file for ESG data ingestion"
)
async def upload_file(
    file: UploadFile = File(..., description="File to upload (.xlsx, .xls, .csv)"),
    facility_name: str = Form(..., description="Facility name"),
    reporting_period: str = Form(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$", description="Reporting period (YYYY-MM)"),
    db: Session = Depends(get_db)
):
    """Upload and ingest a file"""
    logger.info(f"Received upload request: {file.filename}")
    
    # Validate file type
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in settings.app.allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {', '.join(settings.app.allowed_extensions)}"
        )
    
    # Validate file size
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Reset to beginning
    
    max_size = settings.app.max_file_size_mb * 1024 * 1024
    if file_size > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size: {settings.app.max_file_size_mb}MB"
        )
    
    try:
        # Create ingestion service
        service = IngestionService(db)
        
        # Generate upload ID and save file
        result = service.ingest_file_from_upload(file, facility_name, reporting_period)
        
        return UploadResponse(
            upload_id=result.upload_id,
            filename=result.filename,
            status="completed",
            detected_headers=result.headers,
            preview_data=result.preview
        )
        
    except UnsupportedFileTypeError as e:
        logger.error(f"Unsupported file type: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except ParseError as e:
        logger.error(f"Parse error: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to parse file: {str(e)}"
        )
    except Exception as e:
        logger.exception(f"Unexpected error during upload: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during file processing"
        )


@router.get(
    "/status/{upload_id}",
    response_model=UploadStatusResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Upload not found"}
    },
    summary="Get upload status",
    description="Check the processing status of an uploaded file"
)
async def get_upload_status(
    upload_id: UUID,
    db: Session = Depends(get_db)
):
    """Get upload status by ID"""
    logger.info(f"Checking status for upload: {upload_id}")
    
    service = IngestionService(db)
    upload = service.get_upload_status(upload_id)
    
    if not upload:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Upload {upload_id} not found"
        )
    
    # Calculate progress based on status
    progress_map = {
        UploadStatus.PENDING: 0.0,
        UploadStatus.PROCESSING: 50.0,
        UploadStatus.COMPLETED: 100.0,
        UploadStatus.FAILED: 0.0
    }
    
    return UploadStatusResponse(
        upload_id=upload.id,
        status=upload.status.value,
        progress=progress_map.get(upload.status, 0.0),
        message=upload.metadata.get("error") if upload.status == UploadStatus.FAILED else None,
        created_at=upload.created_at,
        updated_at=upload.updated_at
    )


@router.get(
    "/preview/{upload_id}",
    response_model=Dict,
    responses={
        404: {"model": ErrorResponse, "description": "Upload not found"}
    },
    summary="Get data preview",
    description="Get first 10 rows of uploaded data with headers and types"
)
async def get_preview(
    upload_id: UUID,
    db: Session = Depends(get_db)
):
    """Get preview of uploaded data"""
    logger.info(f"Getting preview for upload: {upload_id}")
    
    service = IngestionService(db)
    upload = service.get_upload_status(upload_id)
    
    if not upload:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Upload {upload_id} not found"
        )
    
    if upload.status != UploadStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Upload is not completed. Current status: {upload.status.value}"
        )
    
    # Get preview from metadata or regenerate
    metadata = upload.metadata or {}
    
    return {
        "upload_id": str(upload_id),
        "filename": upload.filename,
        "headers": metadata.get("column_names", []),
        "data_types": metadata.get("data_types", {}),
        "row_count": metadata.get("row_count", 0),
        "preview_note": "Preview data available in upload metadata"
    }


@router.delete(
    "/{upload_id}",
    status_code=status.HTTP_200_OK,
    responses={
        404: {"model": ErrorResponse, "description": "Upload not found"}
    },
    summary="Delete upload",
    description="Soft delete an upload (marks as deleted, keeps file for audit)"
)
async def delete_upload(
    upload_id: UUID,
    db: Session = Depends(get_db)
):
    """Soft delete an upload"""
    logger.info(f"Deleting upload: {upload_id}")
    
    upload = db.query(Upload).filter(Upload.id == upload_id).first()
    
    if not upload:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Upload {upload_id} not found"
        )
    
    # Soft delete - update status instead of removing record
    upload.status = UploadStatus.FAILED  # Using FAILED as deleted status
    upload.metadata = upload.metadata or {}
    upload.metadata["deleted"] = True
    
    db.commit()
    
    logger.info(f"Successfully deleted upload: {upload_id}")
    
    return {
        "message": "Upload deleted successfully",
        "upload_id": str(upload_id),
        "note": "File kept for audit purposes"
    }


@router.get(
    "/list",
    response_model=List[UploadStatusResponse],
    summary="List uploads",
    description="List recent uploads with pagination"
)
async def list_uploads(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """List recent uploads"""
    logger.info(f"Listing uploads (limit={limit}, offset={offset})")
    
    service = IngestionService(db)
    uploads = service.list_uploads(limit=limit, offset=offset)
    
    return [
        UploadStatusResponse(
            upload_id=upload.id,
            status=upload.status.value,
            progress=100.0 if upload.status == UploadStatus.COMPLETED else 0.0,
            message=None,
            created_at=upload.created_at,
            updated_at=upload.updated_at
        )
        for upload in uploads
    ]
