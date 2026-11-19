from datetime import datetime, timezone
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db, check_db_connection
from app.schemas.health import HealthResponse

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="System Health Check",
    description="Check the operational health of the API and its underlying SQLite database.",
)
def get_health(db: Session = Depends(get_db)):
    db_connected = check_db_connection()
    db_status = "connected" if db_connected else "disconnected"

    return HealthResponse(
        status="healthy" if db_connected else "degraded",
        project=settings.PROJECT_NAME,
        version=settings.VERSION,
        timestamp=datetime.now(timezone.utc),
        database_status=db_status,
        environment=settings.ENVIRONMENT,
        details={
            "database": "sqlite",
            "cors_origins": settings.BACKEND_CORS_ORIGINS,
        },
    )

