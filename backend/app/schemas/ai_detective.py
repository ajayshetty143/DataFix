from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class AIDetectiveRecommendation(BaseModel):
    issue_id: str = Field(..., description="Unique issue ID matching detection engine (e.g. ISS-001)")
    issue_category: str = Field(..., description="Issue category (missing_value, duplicate, invalid_format, inconsistency, statistical_anomaly)")
    explanation: str = Field(..., description="Plain-language explanation of the detected issue and impact")
    possible_root_cause: str = Field(..., description="Hypothesized root cause for how this issue entered the dataset")
    recommended_action: str = Field(..., description="Actionable recommendation for remediating or handling this issue")
    recommendation_reason: str = Field(..., description="Justification explaining why this recommendation is appropriate")
    confidence: str = Field(..., description="Confidence level of recommendation: High, Medium, or Low")
    human_review_required: bool = Field(..., description="True if human domain oversight is recommended before applying")


class AIDetectiveReportResponse(BaseModel):
    dataset_id: str
    model_used: str
    total_recommendations: int
    executive_summary: Optional[str] = Field(
        None,
        description="High-level executive summary of dataset health, patterns, and repair priorities"
    )
    recommendations: List[AIDetectiveRecommendation] = Field(
        default_factory=list,
        description="List of AI recommendations linked directly to detected issue IDs"
    )
    generated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when the AI detective report was generated"
    )
