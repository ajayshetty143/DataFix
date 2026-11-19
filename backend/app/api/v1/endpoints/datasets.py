import os
import json
from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, Query, status, HTTPException
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.dataset import (
    DatasetProfileResponse,
    PaginatedPreviewResponse,
    DatasetListItem,
)
from app.schemas.quality import QualityReportResponse
from app.schemas.ai_detective import AIDetectiveReportResponse
from app.schemas.repair import (
    RepairResponse,
    RepairUpdate,
    RepairListResponse,
    RepairApplyResponse,
)
from app.schemas.validation import (
    ValidationReportResponse,
    AuditLogResponse,
    AuditLogItem,
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
from app.services.detection.engine import QualityDetectionEngine
from app.services.gemini_service import GeminiDetectiveService
from app.services.repair_service import RepairService
from app.services.validation_service import ValidationService

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

    # 4. Run data quality detection engine automatically
    quality_data = QualityDetectionEngine.analyze(
        df=df,
        dataset_id=dataset_id,
        filename=file.filename or "unknown",
    )

    # 5. Save metadata into SQLite
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

    # Save initial quality json
    record.quality_json = json.dumps(quality_data)
    db.commit()
    db.refresh(record)

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


@router.post(
    "/{dataset_id}/analyze",
    response_model=QualityReportResponse,
    summary="Run Data Quality Analysis",
    description="Execute the 5-dimension intelligent data quality detection engine on the dataset.",
)
def analyze_dataset_quality(
    dataset_id: str,
    db: Session = Depends(get_db),
):
    record = get_dataset_record(db, dataset_id)
    df = load_dataframe_from_file(record.file_path, record.file_type)

    quality_data = QualityDetectionEngine.analyze(
        df=df,
        dataset_id=record.id,
        filename=record.filename,
    )

    record.quality_json = json.dumps(quality_data)
    db.commit()
    db.refresh(record)

    return quality_data


@router.get(
    "/{dataset_id}/quality",
    response_model=QualityReportResponse,
    summary="Get Data Quality Analysis Report",
    description="Retrieve the latest data quality report for the dataset.",
)
def get_dataset_quality(
    dataset_id: str,
    db: Session = Depends(get_db),
):
    record = get_dataset_record(db, dataset_id)
    if record.quality_json:
        try:
            return json.loads(record.quality_json)
        except Exception:
            pass

    # If not yet analyzed, run analysis on demand
    df = load_dataframe_from_file(record.file_path, record.file_type)
    quality_data = QualityDetectionEngine.analyze(
        df=df,
        dataset_id=record.id,
        filename=record.filename,
    )
    record.quality_json = json.dumps(quality_data)
    db.commit()
    db.refresh(record)

    return quality_data


@router.post(
    "/{dataset_id}/ai-detective",
    response_model=AIDetectiveReportResponse,
    summary="Run Gemini AI Detective Analysis",
    description="Analyze detected quality issues using Google Gemini AI to provide root cause analysis, recommendations, and confidence ratings.",
)
def run_ai_detective(
    dataset_id: str,
    db: Session = Depends(get_db),
):
    record = get_dataset_record(db, dataset_id)

    # 1. Retrieve or run quality detection
    if record.quality_json:
        try:
            quality_data = json.loads(record.quality_json)
        except Exception:
            quality_data = None
    else:
        quality_data = None

    if not quality_data:
        df = load_dataframe_from_file(record.file_path, record.file_type)
        quality_data = QualityDetectionEngine.analyze(
            df=df,
            dataset_id=record.id,
            filename=record.filename,
        )
        record.quality_json = json.dumps(quality_data)
        db.commit()

    issues = quality_data.get("summary", {}).get("issues", [])
    profile_data = json.loads(record.profile_json) if record.profile_json else {}
    column_profiles = profile_data.get("column_profiles", [])

    # 2. Invoke Gemini AI Detective service
    report = GeminiDetectiveService.analyze_issues(
        dataset_id=record.id,
        filename=record.filename,
        total_rows=record.total_rows,
        total_columns=record.total_columns,
        issues=issues,
        column_profiles=column_profiles,
    )

    # 3. Cache AI report in database
    record.ai_detective_json = json.dumps(report.model_dump(mode="json"))
    db.commit()
    db.refresh(record)

    return report


@router.get(
    "/{dataset_id}/ai-detective",
    response_model=AIDetectiveReportResponse,
    summary="Get Gemini AI Detective Report",
    description="Retrieve the cached AI Detective report or generate it on demand.",
)
def get_ai_detective(
    dataset_id: str,
    db: Session = Depends(get_db),
):
    record = get_dataset_record(db, dataset_id)
    if record.ai_detective_json:
        try:
            cached_data = json.loads(record.ai_detective_json)
            return AIDetectiveReportResponse(**cached_data)
        except Exception:
            pass

    # If not yet generated, run on demand
    return run_ai_detective(dataset_id=dataset_id, db=db)


# -----------------------------------------------------------------------------
# PHASE 5: SAFE DATA REPAIR ENGINE ENDPOINTS
# -----------------------------------------------------------------------------

@router.post(
    "/{dataset_id}/repairs/propose",
    response_model=RepairListResponse,
    summary="Generate Data Repair Proposals",
    description="Deterministically generate candidate repair proposals based on Phase 3 quality issues and Phase 4 Gemini context.",
)
def propose_repairs(
    dataset_id: str,
    db: Session = Depends(get_db),
):
    RepairService.propose_repairs(db=db, dataset_id=dataset_id)
    return RepairService.get_repairs(db=db, dataset_id=dataset_id)


@router.get(
    "/{dataset_id}/repairs",
    response_model=RepairListResponse,
    summary="Get Repair Proposals and Status",
    description="Retrieve all proposed, approved, rejected, and applied repairs for a dataset.",
)
def get_repairs(
    dataset_id: str,
    db: Session = Depends(get_db),
):
    repairs_resp = RepairService.get_repairs(db=db, dataset_id=dataset_id)
    # If no repairs have been generated yet, automatically propose them
    if repairs_resp.summary.total == 0:
        RepairService.propose_repairs(db=db, dataset_id=dataset_id)
        return RepairService.get_repairs(db=db, dataset_id=dataset_id)
    return repairs_resp


@router.patch(
    "/{dataset_id}/repairs/{repair_id}",
    response_model=RepairResponse,
    summary="Edit Proposed Repair Value",
    description="Customize the proposed value for an individual repair proposal prior to approval.",
)
def update_repair(
    dataset_id: str,
    repair_id: str,
    body: RepairUpdate,
    db: Session = Depends(get_db),
):
    return RepairService.update_repair(
        db=db,
        dataset_id=dataset_id,
        repair_id=repair_id,
        proposed_value=body.proposed_value,
    )


@router.post(
    "/{dataset_id}/repairs/{repair_id}/approve",
    response_model=RepairResponse,
    summary="Approve Individual Repair Proposal",
    description="Approve a single repair proposal for subsequent execution.",
)
def approve_repair(
    dataset_id: str,
    repair_id: str,
    db: Session = Depends(get_db),
):
    return RepairService.approve_repair(
        db=db,
        dataset_id=dataset_id,
        repair_id=repair_id,
    )


@router.post(
    "/{dataset_id}/repairs/{repair_id}/reject",
    response_model=RepairResponse,
    summary="Reject Individual Repair Proposal",
    description="Explicitly reject a repair proposal so it is excluded from application.",
)
def reject_repair(
    dataset_id: str,
    repair_id: str,
    db: Session = Depends(get_db),
):
    return RepairService.reject_repair(
        db=db,
        dataset_id=dataset_id,
        repair_id=repair_id,
    )


@router.post(
    "/{dataset_id}/repairs/apply-approved",
    response_model=RepairApplyResponse,
    summary="Execute Approved Repairs",
    description="Safely apply all user-approved repairs onto a separate working copy, preserving original uploaded files.",
)
def apply_approved_repairs(
    dataset_id: str,
    db: Session = Depends(get_db),
):
    return RepairService.apply_approved_repairs(
        db=db,
        dataset_id=dataset_id,
    )


@router.get(
    "/{dataset_id}/repairs/preview",
    response_model=PaginatedPreviewResponse,
    summary="Preview Repaired Working Dataset",
    description="Preview the paginated working dataset generated after approved repairs are applied.",
)
def preview_repaired_dataset(
    dataset_id: str,
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    db: Session = Depends(get_db),
):
    record = get_dataset_record(db, dataset_id)
    if not record.repaired_file_path or not os.path.exists(record.repaired_file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No repaired working dataset exists yet. Please approve and apply repairs first.",
        )

    df_repaired = load_dataframe_from_file(record.repaired_file_path, record.file_type)
    paginated = paginate_dataframe(df_repaired, page=page, page_size=page_size)

    return PaginatedPreviewResponse(
        dataset_id=record.id,
        filename=f"Repaired - {record.filename}",
        total_rows=paginated["total_rows"],
        total_pages=paginated["total_pages"],
        page=paginated["page"],
        page_size=paginated["page_size"],
        columns=paginated["columns"],
        column_types=paginated["column_types"],
        rows=paginated["rows"],
    )


@router.get(
    "/{dataset_id}/repairs/download",
    summary="Download Repaired Dataset",
    description="Download the cleaned working dataset as a CSV or Excel file.",
)
def download_repaired_dataset(
    dataset_id: str,
    db: Session = Depends(get_db),
):
    record = get_dataset_record(db, dataset_id)
    if not record.repaired_file_path or not os.path.exists(record.repaired_file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No repaired working dataset exists for download.",
        )

    ext = "csv" if record.file_type == "csv" else "xlsx"
    clean_name = f"repaired_{record.filename}"
    media_type = "text/csv" if ext == "csv" else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    return FileResponse(
        path=record.repaired_file_path,
        filename=clean_name,
        media_type=media_type,
    )


# ============================================================================
# Phase 6: Validation, Audit Log, and Export Endpoints
# ============================================================================

@router.get(
    "/{dataset_id}/validation",
    response_model=ValidationReportResponse,
    summary="Get Repair Validation Report",
    description="Compare pre-repair and post-repair quality metrics, showing resolved and remaining issues.",
)
def get_validation_report(
    dataset_id: str,
    db: Session = Depends(get_db),
):
    return ValidationService.validate_repairs(db=db, dataset_id=dataset_id, force_recompute=False)


@router.post(
    "/{dataset_id}/validate",
    response_model=ValidationReportResponse,
    summary="Execute Repair Validation",
    description="Re-run deterministic detection on repaired dataset to verify quality improvements and identify remaining issues.",
)
def run_validation(
    dataset_id: str,
    db: Session = Depends(get_db),
):
    return ValidationService.validate_repairs(db=db, dataset_id=dataset_id, force_recompute=True)


@router.get(
    "/{dataset_id}/audit-log",
    response_model=AuditLogResponse,
    summary="Get Modification Audit Log",
    description="Retrieve structured modification history detailing every proposed, approved, rejected, or applied repair.",
)
def get_audit_log(
    dataset_id: str,
    db: Session = Depends(get_db),
):
    entries = ValidationService.get_audit_log(db=db, dataset_id=dataset_id)
    return AuditLogResponse(
        dataset_id=dataset_id,
        total_entries=len(entries),
        entries=entries,
    )


@router.get(
    "/{dataset_id}/export/cleaned-csv",
    summary="Export Cleaned CSV Dataset",
    description="Download the verified cleaned dataset formatted as standard CSV, preserving the original uploaded file.",
)
def export_cleaned_csv(
    dataset_id: str,
    db: Session = Depends(get_db),
):
    csv_path, clean_filename = ValidationService.get_cleaned_csv_path(db=db, dataset_id=dataset_id)
    return FileResponse(
        path=csv_path,
        filename=clean_filename,
        media_type="text/csv",
    )


@router.get(
    "/{dataset_id}/export/report",
    summary="Export Data Quality & Validation Report",
    description="Download comprehensive data-quality report with before/after scores, resolved issues, remaining issues, and repair stats as JSON.",
)
def export_quality_report(
    dataset_id: str,
    db: Session = Depends(get_db),
):
    report_dict = ValidationService.generate_quality_report_dict(db=db, dataset_id=dataset_id)
    report_json = json.dumps(report_dict, indent=2)
    return Response(
        content=report_json,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="data_quality_report_{dataset_id[:8]}.json"'
        },
    )


@router.get(
    "/{dataset_id}/export/audit-log",
    summary="Export Modification History",
    description="Download complete modification history and repair audit log as CSV or JSON.",
)
def export_audit_log(
    dataset_id: str,
    format: str = Query("csv", description="Export format: 'csv' or 'json'"),
    db: Session = Depends(get_db),
):
    if format.lower() == "json":
        entries = ValidationService.get_audit_log(db=db, dataset_id=dataset_id)
        return Response(
            content=json.dumps(entries, indent=2),
            media_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="audit_log_{dataset_id[:8]}.json"'
            },
        )

    csv_content = ValidationService.export_audit_log_csv(db=db, dataset_id=dataset_id)
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="audit_log_{dataset_id[:8]}.csv"'
        },
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
