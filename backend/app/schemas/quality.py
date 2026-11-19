from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class QualityIssueResponse(BaseModel):
    id: str = Field(..., json_schema_extra={"example": "ISS-001"})
    category: str = Field(..., json_schema_extra={"example": "missing_value"})
    severity: str = Field(..., json_schema_extra={"example": "warning"})
    column: Optional[str] = Field(None, json_schema_extra={"example": "email"})
    title: str = Field(..., json_schema_extra={"example": "Missing Values in 'email'"})
    description: str = Field(..., json_schema_extra={"example": "Found 4 missing values (26.67%) in column 'email'."})
    row_indices: List[int] = Field(default_factory=list, json_schema_extra={"example": [2, 5, 7, 11]})
    affected_count: int = Field(..., json_schema_extra={"example": 4})
    sample_values: List[Any] = Field(default_factory=list)
    suggested_action: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class QualitySummaryResponse(BaseModel):
    total_issues: int
    total_affected_rows: int
    total_affected_columns: int
    quality_score: float
    by_category: Dict[str, int]
    by_severity: Dict[str, int]
    issues: List[QualityIssueResponse]
    heatmap: List[Dict[str, Any]] = Field(default_factory=list)


class QualityReportResponse(BaseModel):
    dataset_id: str
    filename: str
    total_rows: int
    total_columns: int
    columns: List[str] = Field(default_factory=list)
    analyzed_at: datetime
    summary: QualitySummaryResponse
