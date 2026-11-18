from typing import List
import datetime as dt
from fastapi import APIRouter, Depends, HTTPException
from ..i18n import tr
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user

router = APIRouter(prefix="/goals", tags=["goals"])


@router.post("", response_model=schemas.GoalOut, status_code=201)
def create_goal(
    payload: schemas.GoalCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    goal = models.Goal(user_id=current_user.id, **payload.model_dump())
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return goal


@router.get("", response_model=List[schemas.GoalOut])
def list_goals(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return db.query(models.Goal).filter(models.Goal.user_id == current_user.id).all()


def _own_goal(db: Session, user: models.User, goal_id: int) -> models.Goal:
    goal = db.query(models.Goal).filter(
        models.Goal.id == goal_id, models.Goal.user_id == user.id
    ).first()
    if not goal:
        raise HTTPException(status_code=404, detail=tr("Goal not found"))
    return goal


@router.patch("/{goal_id}", response_model=schemas.GoalOut)
def update_goal(
    goal_id: int,
    payload: schemas.GoalUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    goal = _own_goal(db, current_user, goal_id)
    for k, v in payload.model_dump(exclude_unset=True).items():
        if v is not None:
            setattr(goal, k, v)
    db.commit()
    db.refresh(goal)
    return goal


@router.post("/{goal_id}/contribute", response_model=schemas.GoalOut)
def contribute(
    goal_id: int,
    payload: schemas.GoalContributionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Add money to (or take money out of) a goal; saved amount never drops below 0."""
    goal = _own_goal(db, current_user, goal_id)
    if payload.amount == 0:
        raise HTTPException(status_code=422, detail=tr("Enter an amount greater than zero."))
    current = goal.saved_amount or 0.0
    if payload.amount < 0 and -payload.amount > current + 1e-9:
        raise HTTPException(status_code=422, detail=tr("You can't take out more than you've saved."))
    goal.saved_amount = round(current + payload.amount, 2)
    db.add(models.GoalContribution(goal_id=goal.id, amount=payload.amount, note=payload.note or ""))
    db.commit()
    db.refresh(goal)
    return goal


@router.get("/{goal_id}/history", response_model=List[schemas.GoalContributionOut])
def history(
    goal_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return _own_goal(db, current_user, goal_id).contributions[:50]


@router.delete("/{goal_id}", status_code=204)
def delete_goal(
    goal_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    goal = db.query(models.Goal).filter(
        models.Goal.id == goal_id, models.Goal.user_id == current_user.id
    ).first()
    if not goal:
        raise HTTPException(status_code=404, detail=tr("Goal not found"))
    db.delete(goal)
    db.commit()
    return None
