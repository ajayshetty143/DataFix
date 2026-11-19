from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class RepairResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Internal UUID of repair record")
    repair_id: str = Field(..., description="Human-readable repair identifier (e.g. REP-001)")
    dataset_id: str = Field(..., description="Associated dataset ID")
    issue_id: str = Field(..., description="Associated detection engine issue ID (e.g. ISS-001)")
    repair_type: str = Field(..., description="Type of repair: missing_imputation, deduplication, format_correction, category_normalization, anomaly_review")
    column_name: Optional[str] = Field(None, description="Affected column name, or None for whole-row operations")
    row_index: int = Field(..., description="0-indexed row position in dataset")
    original_value: Optional[str] = Field(None, description="Current value at the row/column before repair")
    proposed_value: Optional[str] = Field(None, description="Proposed replacement value, or None if manual input needed")
    applied_value: Optional[str] = Field(None, description="Value actually applied to working dataset")
    explanation: str = Field(..., description="Justification and explanation of proposed repair")
    confidence: str = Field(..., description="Confidence level: High, Medium, or Low")
    human_review_required: bool = Field(..., description="Whether human review is required before approval")
    status: str = Field(..., description="Current status: pending, approved, rejected, applied, failed")
    error_message: Optional[str] = Field(None, description="Failure reason if validation or application failed")
    created_at: datetime
    updated_at: datetime
    applied_at: Optional[datetime] = None


class RepairUpdate(BaseModel):
    proposed_value: Optional[str] = Field(None, description="User-edited proposed value")


class RepairSummary(BaseModel):
    total: int = 0
    pending: int = 0
    approved: int = 0
    rejected: int = 0
    applied: int = 0
    failed: int = 0


class RepairListResponse(BaseModel):
    dataset_id: str
    summary: RepairSummary
    has_repaired_dataset: bool = False
    repaired_file_path: Optional[str] = None
    repaired_at: Optional[datetime] = None
    repairs: List[RepairResponse] = []


class RepairResultItem(BaseModel):
    repair_id: str
    status: str  # "applied" or "failed"
    message: str
    column_name: Optional[str] = None
    row_index: int
    before: Optional[str] = None
    after: Optional[str] = None


class RepairApplyResponse(BaseModel):
    dataset_id: str
    applied_count: int
    failed_count: int
    repaired_file_path: str
    repaired_at: datetime
    results: List[RepairResultItem] = []
