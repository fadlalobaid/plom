"""Admin-only statistics API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.db.session import get_db
from app.schemas.statistics import StatisticsOverviewResponse
from app.services.statistics_service import get_statistics_overview

router = APIRouter(
    prefix="/statistics",
    tags=["statistics"],
    dependencies=[Depends(require_admin)],
)


@router.get("/overview", response_model=StatisticsOverviewResponse)
def get_overview_statistics(
    db: Annotated[Session, Depends(get_db)],
) -> StatisticsOverviewResponse:
    """Return aggregated system statistics for administrators."""
    return get_statistics_overview(db)
