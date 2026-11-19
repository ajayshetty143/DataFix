from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class NumericalStats(BaseModel):
    mean: Optional[float] = Field(None, json_schema_extra={"example": 45.2})
    median: Optional[float] = Field(None, json_schema_extra={"example": 42.0})
    min: Optional[float] = Field(None, json_schema_extra={"example": 10.0})
    max: Optional[float] = Field(None, json_schema_extra={"example": 98.0})
    std: Optional[float] = Field(None, json_schema_extra={"example": 14.5})


class ColumnProfile(BaseModel):
    name: str
    data_type: str  # integer, float, string, datetime, boolean
    null_count: int
    null_percentage: float
    unique_count: int
    is_numerical: bool
    stats: Optional[NumericalStats] = None
    sample_values: Optional[List[Any]] = None


class DatasetProfileResponse(BaseModel):
    id: str
    filename: str
    file_size: int
    file_size_formatted: str
    file_type: str
    total_rows: int
    total_columns: int
    columns: List[str]
    column_profiles: List[ColumnProfile]
    created_at: datetime


class PaginatedPreviewResponse(BaseModel):
    dataset_id: str
    filename: str
    total_rows: int
    total_pages: int
    page: int
    page_size: int
    columns: List[str]
    column_types: Dict[str, str]
    rows: List[Dict[str, Any]]


class DatasetListItem(BaseModel):
    id: str
    filename: str
    file_size: int
    file_size_formatted: str
    file_type: str
    total_rows: int
    total_columns: int
    created_at: datetime
