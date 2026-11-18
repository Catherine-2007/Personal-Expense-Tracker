import json
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user
from ..i18n import tr, tr_stored
from ..services import trigger_engine, xai_engine, counterfactual, recurring, pulse, lab, anomaly, persona

router = APIRouter(prefix="/insights", tags=["insights"])


def _trigger_to_out(t: models.Trigger) -> schemas.TriggerOut:
    return schemas.TriggerOut(
        id=t.id, context_key=t.context_key, category_affected=t.category_affected,
        description=tr_stored(t.description), evidence=[tr_stored(e) for e in json.loads(t.evidence_json)],
        confidence=t.confidence, occurrences=t.occurrences, active=t.active,
    )


@router.post("/triggers/refresh", response_model=List[schemas.TriggerOut])
def refresh_triggers(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Re-runs the mining pipeline over the user's full expense history."""
    expenses = db.query(models.Expense).filter(models.Expense.user_id == current_user.id).all()
    candidates = trigger_engine.discover_triggers(expenses)
    rows = trigger_engine.persist_triggers(db, current_user.id, candidates)
    return [_trigger_to_out(t) for t in rows]


@router.get("/triggers", response_model=List[schemas.TriggerOut])
def list_triggers(
    active_only: bool = True,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    q = db.query(models.Trigger).filter(models.Trigger.user_id == current_user.id)
    if active_only:
        q = q.filter(models.Trigger.active == True)
    rows = q.order_by(models.Trigger.confidence.desc()).all()
    return [_trigger_to_out(t) for t in rows]


@router.get("/triggers/{trigger_id}/explain")
def explain(
    trigger_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    trigger = db.query(models.Trigger).filter(
        models.Trigger.id == trigger_id, models.Trigger.user_id == current_user.id
    ).first()
    if not trigger:
        raise HTTPException(status_code=404, detail=tr("Trigger not found"))
    return xai_engine.explain_trigger(trigger)


@router.post("/counterfactual")
def run_counterfactual(
    payload: schemas.CounterfactualRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return counterfactual.simulate(
        db, current_user.id, payload.category, payload.times_per_week_reduction,
        payload.avg_amount_override,
    )


@router.get("/recurring")
def recurring_charges(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Subscription Radar: merchants that bill on a regular rhythm."""
    expenses = db.query(models.Expense).filter(models.Expense.user_id == current_user.id).all()
    found = recurring.detect_recurring(expenses)
    return {
        "items": found,
        "total_monthly": round(sum(r["monthly_cost"] for r in found), 2),
        "total_annual": round(sum(r["annual_cost"] for r in found), 2),
    }


@router.get("/safe-to-spend")
def safe_to_spend(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return pulse.safe_to_spend(db, current_user)


@router.get("/heatmap")
def spending_heatmap(
    weeks: int = 20,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return pulse.heatmap(db, current_user.id, weeks)


@router.get("/anomaly-check")
def anomaly_check(
    amount: float,
    category: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Is this purchase unusual compared with the user's own history?"""
    return anomaly.check_amount(db, current_user.id, category, amount)


@router.get("/anomalies")
def recent_anomalies(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return {"items": anomaly.recent_unusual(db, current_user.id)}


@router.get("/persona")
def spending_persona(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return persona.build_persona(db, current_user.id)


@router.get("/roundup")
def roundup(
    step: int = 10,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return lab.roundup_savings(db, current_user.id, step)


@router.get("/forecast")
def forecast(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return lab.cashflow_forecast(db, current_user)
