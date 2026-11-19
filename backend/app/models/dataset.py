from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, Text
from app.core.database import Base


class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(String(36), primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)  # size in bytes
    file_type = Column(String(20), nullable=False)  # 'csv' or 'excel'
    total_rows = Column(Integer, nullable=False, default=0)
    total_columns = Column(Integer, nullable=False, default=0)
    profile_json = Column(Text, nullable=True)  # JSON string of profiler output
    quality_json = Column(Text, nullable=True)  # JSON string of quality analysis output
    created_at = Column(
        DateTime, 
        default=lambda: datetime.now(timezone.utc), 
        nullable=False
    )
