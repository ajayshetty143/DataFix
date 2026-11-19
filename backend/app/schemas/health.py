from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(..., json_schema_extra={"example": "healthy"})
    project: str = Field(..., json_schema_extra={"example": "DataFix API"})
    version: str = Field(..., json_schema_extra={"example": "0.1.0"})
    timestamp: datetime
    database_status: str = Field(..., json_schema_extra={"example": "connected"})
    environment: str = Field(..., json_schema_extra={"example": "development"})
    details: Optional[Dict[str, Any]] = None
