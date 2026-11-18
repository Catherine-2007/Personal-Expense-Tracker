"""Monthly budgets: one overall limit ("ALL") plus optional per-category limits."""
import datetime as dt
from typing import Dict
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user
from ..i18n import tr, N_

router = APIRouter(prefix="/budgets", tags=["budgets"])

CATEGORIES = ["Food", "Groceries", "Shopping", "Transport", "Bills", "Entertainment", "Health", "Others"]
ALL = "ALL"
WARN_AT = 0.8


def _month_bounds(now: dt.datetime):
    start = dt.datetime(now.year, now.month, 1)
    nxt = dt.datetime(now.year + (now.month == 12), now.month % 12 + 1, 1)
    return start, nxt


def _status(pct: float) -> str:
    return "over" if pct >= 1 else "warn" if pct >= WARN_AT else "ok"


def build(db: Session, user: models.User, now: dt.datetime | None = None) -> dict:
    now = now or dt.datetime.utcnow()
    start, nxt = _month_bounds(now)
    rows = db.query(models.Expense).filter(
        models.Expense.user_id == user.id, models.Expense.timestamp >= start, models.Expense.timestamp < nxt).all()
    spent: Dict[str, float] = {}
    for e in rows:
        spent[e.category] = spent.get(e.category, 0.0) + e.amount
    total = sum(spent.values())
    limits = {b.category: b.monthly_limit for b in db.query(models.Budget).filter(models.Budget.user_id == user.id)}
    days_in_month = (nxt - start).days
    day = now.day

    def item(cat: str, limit: float, used: float) -> dict:
        pct = used / limit if limit else 0.0
        # simple pace projection: at today's rate, where will the month end?
        projected = used / day * days_in_month if day else used
        return {"category": cat, "limit": round(limit, 2), "spent": round(used, 2),
                "remaining": round(limit - used, 2), "pct": round(pct * 100, 1), "status": _status(pct),
                "projected": round(projected, 2), "on_pace": projected <= limit}

    overall = item(ALL, limits[ALL], total) if ALL in limits else None
    items = [item(c, v, spent.get(c, 0.0)) for c, v in limits.items() if c != ALL]
    items.sort(key=lambda x: -x["pct"])
    unbudgeted = [{"category": c, "spent": round(v, 2)} for c, v in sorted(spent.items(), key=lambda kv: -kv[1]) if c not in limits]
    return {"month": now.strftime("%Y-%m"), "overall": overall, "items": items, "unbudgeted": unbudgeted,
            "total_spent": round(total, 2), "days_left": days_in_month - day,
            "categories": CATEGORIES}


@router.get("")
def get_budgets(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return build(db, current_user)


@router.put("/{category}")
def set_budget(category: str, payload: schemas.BudgetSet, db: Session = Depends(get_db),
               current_user: models.User = Depends(get_current_user)):
    if category != ALL and category not in CATEGORIES:
        raise HTTPException(status_code=422, detail=tr("Unknown category"))
    b = db.query(models.Budget).filter(models.Budget.user_id == current_user.id, models.Budget.category == category).first()
    if b:
        b.monthly_limit = payload.monthly_limit
    else:
        db.add(models.Budget(user_id=current_user.id, category=category, monthly_limit=payload.monthly_limit))
    db.commit()
    return build(db, current_user)


@router.delete("/{category}")
def delete_budget(category: str, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    db.query(models.Budget).filter(models.Budget.user_id == current_user.id, models.Budget.category == category).delete()
    db.commit()
    return build(db, current_user)
