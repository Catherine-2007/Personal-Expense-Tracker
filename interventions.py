from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user
from ..i18n import tr, tr_stored
from ..services import intervention_engine


def _out(iv: models.Intervention) -> schemas.InterventionOut:
    """Stored descriptions are English; show them in the reader's language."""
    out = schemas.InterventionOut.model_validate(iv)
    return out.model_copy(update={"description": tr_stored(out.description)})

router = APIRouter(prefix="/interventions", tags=["interventions"])


@router.post("/suggest/{trigger_id}", response_model=schemas.InterventionOut)
def suggest(
    trigger_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    trigger = db.query(models.Trigger).filter(
        models.Trigger.id == trigger_id, models.Trigger.user_id == current_user.id
    ).first()
    if not trigger:
        raise HTTPException(status_code=404, detail=tr("Trigger not found"))

    context_expenses = [
        e for e in db.query(models.Expense).filter(
            models.Expense.user_id == current_user.id,
            models.Expense.category == trigger.category_affected,
        ).all()
    ]
    return _out(intervention_engine.suggest_intervention(db, current_user, trigger, context_expenses))


@router.get("", response_model=List[schemas.InterventionOut])
def list_interventions(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return [_out(i) for i in db.query(models.Intervention).filter(models.Intervention.user_id == current_user.id).all()]


@router.post("/{intervention_id}/measure", response_model=schemas.InterventionOut)
def measure(
    intervention_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    iv = db.query(models.Intervention).filter(
        models.Intervention.id == intervention_id, models.Intervention.user_id == current_user.id
    ).first()
    if not iv:
        raise HTTPException(status_code=404, detail=tr("Intervention not found"))
    return _out(intervention_engine.measure_effectiveness(db, iv))


@router.post("/{intervention_id}/feedback", response_model=schemas.InterventionOut)
def feedback(
    intervention_id: int,
    payload: schemas.FeedbackIn,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    iv = db.query(models.Intervention).filter(
        models.Intervention.id == intervention_id, models.Intervention.user_id == current_user.id
    ).first()
    if not iv:
        raise HTTPException(status_code=404, detail=tr("Intervention not found"))
    return _out(intervention_engine.submit_feedback(db, iv, payload.feedback))
