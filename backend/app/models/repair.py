import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text
from app.core.database import Base


class RepairRecord(Base):
    __tablename__ = "repair_records"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    repair_id = Column(String(20), nullable=False, index=True)  # e.g. REP-001
    dataset_id = Column(String(36), nullable=False, index=True)  # References datasets.id
    issue_id = Column(String(20), nullable=False, index=True)  # References issue ID (e.g. ISS-001)
    repair_type = Column(String(40), nullable=False)  # missing_imputation, deduplication, format_correction, category_normalization, anomaly_review
    column_name = Column(String(255), nullable=True)  # None if row-level operation like deduplication
    row_index = Column(Integer, nullable=False)  # 0-indexed row number in the dataset
    original_value = Column(Text, nullable=True)  # Exact string representation before repair
    proposed_value = Column(Text, nullable=True)  # Suggested replacement value (None if manual input needed)
    applied_value = Column(Text, nullable=True)  # Value actually applied to the working dataset
    explanation = Column(Text, nullable=False)  # Plain-English description of repair operation
    confidence = Column(String(20), nullable=False, default="Medium")  # High, Medium, Low
    human_review_required = Column(Boolean, nullable=False, default=True)  # True if domain oversight is mandatory
    status = Column(String(20), nullable=False, default="pending")  # pending, approved, rejected, applied, failed
    error_message = Column(Text, nullable=True)  # Validation or execution failure details if any
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    applied_at = Column(DateTime, nullable=True)
