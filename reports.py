from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..deps import get_current_user
from ..services import report_generator

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/monthly")
def monthly_report(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return report_generator.build_monthly_report(db, current_user.id)
