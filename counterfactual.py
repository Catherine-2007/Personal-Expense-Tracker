"""
Counterfactual Simulator (infographic block 3.10).

Answers "what if you changed this habit?" by projecting monthly spend under
a hypothetical reduction in frequency for a given category, using the
user's own recent average transaction size (not a generic assumption).
"""
from __future__ import annotations
import datetime as dt
from typing import Optional
from sqlalchemy.orm import Session
from .. import models

WEEKS_PER_MONTH = 4.345


def simulate(db: Session, user_id: int, category: str, times_per_week_reduction: float,
             avg_amount_override: Optional[float] = None) -> dict:
    since = dt.datetime.utcnow() - dt.timedelta(days=90)
    recent = (
        db.query(models.Expense)
        .filter(
            models.Expense.user_id == user_id,
            models.Expense.category == category,
            models.Expense.timestamp >= since,
        )
        .all()
    )

    if avg_amount_override is not None:
        avg_amount = avg_amount_override
    elif recent:
        avg_amount = sum(e.amount for e in recent) / len(recent)
    else:
        avg_amount = 0.0

    current_monthly_spend = avg_amount * (len(recent) / 3.0) if recent else 0.0  # 3 months window
    projected_monthly_savings = avg_amount * times_per_week_reduction * WEEKS_PER_MONTH
    projected_monthly_spend = max(current_monthly_spend - projected_monthly_savings, 0.0)

    return {
        "category": category,
        "current_monthly_spend": round(current_monthly_spend, 2),
        "avg_transaction": round(avg_amount, 2),
        "reduction_per_week": times_per_week_reduction,
        "projected_monthly_spend": round(projected_monthly_spend, 2),
        "estimated_monthly_savings": round(min(projected_monthly_savings, current_monthly_spend), 2),
        "estimated_annual_savings": round(min(projected_monthly_savings, current_monthly_spend) * 12, 2),
    }
