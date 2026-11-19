import json
from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, Query, status, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.dataset import (
    DatasetProfileResponse,
    PaginatedPreviewResponse,
    DatasetListItem,
)
from app.services.dataset_service import (
    save_uploaded_file,
    load_dataframe_from_file,
    paginate_dataframe,
    save_dataset_record,
    get_dataset_record,
    list_dataset_records,
)
from app.services.profiler import profile_dataframe, format_file_size

router = APIRouter()


@router.post(
    "/upload",
    response_model=DatasetProfileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and Profile Dataset",
    description="Upload a CSV or Excel (.xlsx) file, validate file size/type, preserve original file, and compute data profiling statistics.",
)
async def upload_dataset(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    # 1. Save uploaded file without modification
    dataset_id, saved_path, file_size, file_type = await save_uploaded_file(file)

    # 2. Parse file into DataFrame safely
    df = load_dataframe_from_file(saved_path, file_type)

    # 3. Generate profiling summary
    profile_data = profile_dataframe(
        df=df,
        file_size=file_size,
        filename=file.filename or "unknown",
        dataset_id=dataset_id,
    )

    # 4. Save metadata into SQLite
    record = save_dataset_record(
        db=db,
        dataset_id=dataset_id,
        filename=file.filename or "unknown",
        file_path=saved_path,
        file_size=file_size,
        file_type=file_type,
        total_rows=profile_data["total_rows"],
        total_columns=profile_data["total_columns"],
        profile_data=profile_data,
    )

    return DatasetProfileResponse(
        id=record.id,
        filename=record.filename,
        file_size=record.file_size,
        file_size_formatted=profile_data["file_size_formatted"],
        file_type=record.file_type,
        total_rows=record.total_rows,
        total_columns=record.total_columns,
        columns=profile_data["columns"],
        column_profiles=profile_data["column_profiles"],
        created_at=record.created_at,
    )


@router.get(
    "/{dataset_id}",
    response_model=DatasetProfileResponse,
    summary="Get Dataset Profile",
    description="Fetch full profiling and column metadata for an uploaded dataset.",
)
def get_dataset(
    dataset_id: str,
    db: Session = Depends(get_db),
):
    record = get_dataset_record(db, dataset_id)
    profile_data = json.loads(record.profile_json) if record.profile_json else {}

    return DatasetProfileResponse(
        id=record.id,
        filename=record.filename,
        file_size=record.file_size,
        file_size_formatted=format_file_size(record.file_size),
        file_type=record.file_type,
        total_rows=record.total_rows,
        total_columns=record.total_columns,
        columns=profile_data.get("columns", []),
        column_profiles=profile_data.get("column_profiles", []),
        created_at=record.created_at,
    )


@router.get(
    "/{dataset_id}/preview",
    response_model=PaginatedPreviewResponse,
    summary="Get Paginated Dataset Preview",
    description="Fetch a paginated slice of dataset rows without loading the entire dataset into memory.",
)
def get_dataset_preview(
    dataset_id: str,
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    db: Session = Depends(get_db),
):
    record = get_dataset_record(db, dataset_id)
    df = load_dataframe_from_file(record.file_path, record.file_type)
    paginated = paginate_dataframe(df, page=page, page_size=page_size)

    return PaginatedPreviewResponse(
        dataset_id=record.id,
        filename=record.filename,
        total_rows=paginated["total_rows"],
        total_pages=paginated["total_pages"],
        page=paginated["page"],
        page_size=paginated["page_size"],
        columns=paginated["columns"],
        column_types=paginated["column_types"],
        rows=paginated["rows"],
    )


@router.get(
    "",
    response_model=List[DatasetListItem],
    summary="List Uploaded Datasets",
    description="Retrieve all previously uploaded datasets.",
)
def list_datasets(
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    records = list_dataset_records(db, limit=limit)
    return [
        DatasetListItem(
            id=r.id,
            filename=r.filename,
            file_size=r.file_size,
            file_size_formatted=format_file_size(r.file_size),
            file_type=r.file_type,
            total_rows=r.total_rows,
            total_columns=r.total_columns,
            created_at=r.created_at,
        )
        for r in records
    ]
