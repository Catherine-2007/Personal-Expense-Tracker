"""
"Pulse" features: Safe-to-Spend-Today and the spending heatmap.

Safe-to-Spend answers the one question people actually have each morning --
"how much can I spend today without hurting my goals?" -- using only the
user's own numbers:

    budget      = monthly income (or, if unknown, their own 3-month baseline)
    reserve     = what their goals need this month (remaining / months left)
    spendable   = budget - reserve - already spent this month
    allowance   = spendable / days left in the month (including today)
"""
from __future__ import annotations

import calendar
import datetime as dt
from collections import defaultdict
from typing import Dict, List

from sqlalchemy.orm import Session

from .. import models
from ..i18n import tr
from . import report_generator as rg


def safe_to_spend(db: Session, user: models.User, now: dt.datetime | None = None) -> Dict:
    now = now or dt.datetime.utcnow()
    start, end = rg._month_bounds(now)
    month_rows = db.query(models.Expense).filter(
        models.Expense.user_id == user.id, models.Expense.timestamp >= start,
        models.Expense.timestamp <= end).all()
    spent_month = sum(e.amount for e in month_rows)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    spent_today = sum(e.amount for e in month_rows if e.timestamp >= today_start)

    if (user.monthly_income or 0) > 0:
        budget, source = float(user.monthly_income), "income"
    else:
        base = rg.self_comparison(db, user.id, now)["personal_baseline_avg"]
        budget, source = (float(base), "baseline") if base > 0 else (0.0, "none")

    if source == "none":
        return {"available": False, "reason": tr("Add your monthly income in Settings (or log a few weeks of expenses) to unlock Safe-to-Spend.")}

    goals = db.query(models.Goal).filter(models.Goal.user_id == user.id).all()
    reserve = 0.0
    for g in goals:
        months_left = max((g.deadline.year - now.year) * 12 + (g.deadline.month - now.month), 1)
        reserve += max(g.target_amount - g.saved_amount, 0.0) / months_left
    # never let goals eat more than 60% of the budget -- keeps the number sane
    reserve = min(reserve, budget * 0.6)

    days_in_month = calendar.monthrange(now.year, now.month)[1]
    days_left = days_in_month - now.day + 1
    spent_before_today = spent_month - spent_today
    spendable = budget - reserve - spent_before_today          # what's left going into today
    daily = max(spendable, 0.0) / days_left
    remaining_today = daily - spent_today

    pct_used = (spent_month / (budget - reserve)) * 100 if (budget - reserve) > 0 else 100.0
    if spendable <= 0:
        status = "over"
    elif remaining_today < 0:
        status = "tight"
    elif spent_today > 0.75 * daily:
        status = "tight"
    else:
        status = "great"

    return {
        "available": True,
        "budget": round(budget, 2),
        "budget_source": source,
        "goals_reserve": round(reserve, 2),
        "spent_month": round(spent_month, 2),
        "spent_today": round(spent_today, 2),
        "days_left": days_left,
        "daily_allowance": round(daily, 2),
        "remaining_today": round(remaining_today, 2),
        "month_remaining": round(max(spendable - spent_today, 0.0), 2),
        "pct_used": round(min(pct_used, 999), 1),
        "status": status,
    }


def heatmap(db: Session, user_id: int, weeks: int = 20, today: dt.date | None = None) -> Dict:
    today = today or dt.datetime.utcnow().date()
    weeks = max(4, min(weeks, 53))
    # align to Monday-start weeks so columns are whole weeks
    end = today
    start = end - dt.timedelta(days=end.weekday() + 7 * (weeks - 1))
    rows = db.query(models.Expense).filter(
        models.Expense.user_id == user_id,
        models.Expense.timestamp >= dt.datetime.combine(start, dt.time.min)).all()
    totals: Dict[dt.date, float] = defaultdict(float)
    counts: Dict[dt.date, int] = defaultdict(int)
    for e in rows:
        d = e.timestamp.date()
        totals[d] += e.amount
        counts[d] += 1

    days: List[Dict] = []
    d = start
    while d <= end:
        days.append({"date": d.isoformat(), "weekday": d.weekday(),
                     "total": round(totals.get(d, 0.0), 2), "count": counts.get(d, 0)})
        d += dt.timedelta(days=1)

    vals = sorted(x["total"] for x in days if x["total"] > 0)
    def q(p):  # quantile on non-zero days -> robust to one huge purchase
        return vals[min(int(len(vals) * p), len(vals) - 1)] if vals else 0.0
    thresholds = [q(0.25), q(0.5), q(0.75)]
    for x in days:
        t = x["total"]
        x["level"] = 0 if t <= 0 else 1 if t <= thresholds[0] else 2 if t <= thresholds[1] else 3 if t <= thresholds[2] else 4

    first_logged = min((e.timestamp.date() for e in rows), default=None)
    first_logged = first_logged.isoformat() if first_logged else None
    busiest = max(days, key=lambda x: x["total"]) if vals else None
    by_wd = defaultdict(float)
    for x in days:
        by_wd[x["weekday"]] += x["total"]
    names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    top_wd = names[max(by_wd, key=by_wd.get)] if vals else None
    return {
        "start": start.isoformat(), "end": end.isoformat(), "weeks": weeks, "days": days,
        # only count days since the person started logging (a brand-new account has 0, not 150)
        "no_spend_days": (sum(1 for x in days if x["total"] == 0 and first_logged and x["date"] >= first_logged
                              and x["date"] <= dt.date.today().isoformat())),
        "busiest_day": busiest, "priciest_weekday": top_wd,
    }
