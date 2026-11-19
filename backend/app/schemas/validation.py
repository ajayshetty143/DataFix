from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict


class RepairSummaryCounts(BaseModel):
    total: int = 0
    applied: int = 0
    rejected: int = 0
    pending: int = 0
    failed: int = 0


class ResolvedIssueItem(BaseModel):
    issue_id: str
    category: str
    column: Optional[str] = None
    title: str
    description: str
    resolved_count: int
    original_affected_count: int


class ValidationReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    dataset_id: str
    filename: str
    original_quality_score: float
    repaired_quality_score: float
    score_improvement: float
    is_fully_clean: bool
    original_issues_count: int
    repaired_issues_count: int
    resolved_issues_count: int
    remaining_issues_count: int
    resolved_issues: List[Dict[str, Any]] = []
    remaining_issues: List[Dict[str, Any]] = []
    repair_summary: RepairSummaryCounts
    validated_at: datetime


class AuditLogItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    repair_id: str
    issue_id: str
    repair_type: str
    column_name: Optional[str] = None
    row_index: int
    row_number: int
    original_value: Optional[str] = None
    new_value: Optional[str] = None
    status: str
    action: str
    confidence: str
    human_review_required: bool
    timestamp: datetime
    error_message: Optional[str] = None


class AuditLogResponse(BaseModel):
    dataset_id: str
    total_entries: int
    entries: List[AuditLogItem] = []
