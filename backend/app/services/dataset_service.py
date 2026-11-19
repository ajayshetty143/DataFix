import os
import re
import json
import math
import uuid
from typing import Tuple, Dict, Any, List, Optional
import pandas as pd
import numpy as np
from fastapi import UploadFile, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.dataset import Dataset
from app.services.profiler import profile_dataframe, detect_column_type, format_file_size


def sanitize_filename(filename: str) -> str:
    """Sanitize user-provided filename to prevent path traversal."""
    clean_name = os.path.basename(filename)
    return re.sub(r'[^a-zA-Z0-9_.-]', '_', clean_name)


async def save_uploaded_file(file: UploadFile) -> Tuple[str, str, int, str]:
    """
    Validate and save uploaded file to disk without modification.
    Returns: (dataset_id, saved_path, file_size, file_type)
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is missing.",
        )

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{ext}'. Allowed extensions are: {', '.join(settings.ALLOWED_EXTENSIONS)}",
        )

    file_type = "csv" if ext == ".csv" else "excel"
    dataset_id = str(uuid.uuid4())
    safe_name = sanitize_filename(file.filename)
    saved_filename = f"{dataset_id}_{safe_name}"
    saved_path = os.path.join(settings.UPLOAD_DIR, saved_filename)

    max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    total_bytes = 0

    try:
        with open(saved_path, "wb") as out_file:
            while chunk := await file.read(1024 * 64):  # 64 KB chunks
                total_bytes += len(chunk)
                if total_bytes > max_bytes:
                    out_file.close()
                    if os.path.exists(saved_path):
                        os.remove(saved_path)
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"File exceeds maximum allowed size of {settings.MAX_FILE_SIZE_MB} MB.",
                    )
                out_file.write(chunk)
    except HTTPException:
        raise
    except Exception as e:
        if os.path.exists(saved_path):
            os.remove(saved_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save uploaded file: {str(e)}",
        )

    if total_bytes == 0:
        if os.path.exists(saved_path):
            os.remove(saved_path)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty (0 bytes).",
        )

    return dataset_id, saved_path, total_bytes, file_type


def load_dataframe_from_file(file_path: str, file_type: str) -> pd.DataFrame:
    """Read CSV or Excel into pandas DataFrame safely with encoding fallbacks."""
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset source file not found on disk.",
        )

    try:
        if file_type == "csv":
            # Attempt UTF-8 first, fallback to common encodings
            try:
                df = pd.read_csv(file_path, encoding="utf-8")
            except UnicodeDecodeError:
                try:
                    df = pd.read_csv(file_path, encoding="latin1")
                except Exception:
                    df = pd.read_csv(file_path, encoding="cp1252")
        else:
            # Excel (.xlsx or .xls)
            df = pd.read_excel(file_path, engine="openpyxl")

        return df
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unable to parse dataset file: {str(e)}",
        )


def clean_row_value(val: Any) -> Any:
    """Ensure all cell values are JSON-serializable (no NaN / Inf / non-standard objects)."""
    if pd.isna(val):
        return None
    if isinstance(val, (np.floating, float)):
        if math.isnan(val) or math.isinf(val):
            return None
        return round(float(val), 6)
    if isinstance(val, (np.integer, int)):
        return int(val)
    if isinstance(val, (np.bool_, bool)):
        return bool(val)
    if isinstance(val, (pd.Timestamp, np.datetime64)):
        return str(val)
    return str(val)


def paginate_dataframe(
    df: pd.DataFrame,
    page: int = 1,
    page_size: int = 20
) -> Dict[str, Any]:
    """Extract paginated slice from DataFrame with sanitized JSON records."""
    total_rows = len(df)
    page_size = max(1, min(page_size, 100))  # Between 1 and 100
    total_pages = max(1, math.ceil(total_rows / page_size)) if total_rows > 0 else 1
    page = max(1, min(page, total_pages))

    start_idx = (page - 1) * page_size
    end_idx = min(start_idx + page_size, total_rows)

    subset = df.iloc[start_idx:end_idx]
    columns = [str(c) for c in df.columns]
    column_types = {str(df.columns[c_idx]): detect_column_type(df.iloc[:, c_idx]) for c_idx in range(len(df.columns))}

    rows = []
    for idx, (_, row) in enumerate(subset.iterrows()):
        row_dict = {"_row_index": start_idx + idx + 1}
        for c_idx in range(len(df.columns)):
            col_name = str(df.columns[c_idx])
            key = col_name if col_name not in row_dict else f"{col_name}_{c_idx}"
            row_dict[key] = clean_row_value(row.iloc[c_idx])
        rows.append(row_dict)

    return {
        "total_rows": total_rows,
        "total_pages": total_pages,
        "page": page,
        "page_size": page_size,
        "columns": columns,
        "column_types": column_types,
        "rows": rows,
    }


def save_dataset_record(
    db: Session,
    dataset_id: str,
    filename: str,
    file_path: str,
    file_size: int,
    file_type: str,
    total_rows: int,
    total_columns: int,
    profile_data: Dict[str, Any],
) -> Dataset:
    """Save dataset metadata and profiling in SQLite."""
    record = Dataset(
        id=dataset_id,
        filename=filename,
        file_path=file_path,
        file_size=file_size,
        file_type=file_type,
        total_rows=total_rows,
        total_columns=total_columns,
        profile_json=json.dumps(profile_data),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_dataset_record(db: Session, dataset_id: str) -> Dataset:
    """Retrieve dataset by ID or raise 404."""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset with ID '{dataset_id}' not found.",
        )
    return dataset


def list_dataset_records(db: Session, limit: int = 50) -> List[Dataset]:
    """List recent dataset uploads."""
    return db.query(Dataset).order_by(Dataset.created_at.desc()).limit(limit).all()
