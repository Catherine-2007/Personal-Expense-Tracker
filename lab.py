"""
"Insight Lab" -- two personal features computed only from the user's own
history (no population benchmarks, no external calls), each returning the
evidence behind its claim so it stays explainable:

  * roundup_savings      : "spare change" -- if every purchase were rounded up
                           to the next step, how much would have quietly
                           been saved (and what it would be by year-end).
  * cashflow_forecast    : a 14-day forward projection of cumulative spend
                           using the user's own weekday pattern + upcoming
                           recurring charges, with a safe/over verdict.
"""
from __future__ import annotations

import datetime as dt
import math
import statistics
from collections import defaultdict
from typing import Dict, List

from sqlalchemy.orm import Session

from .. import models
from ..i18n import tr
from . import recurring as recurring_svc


def _expenses(db: Session, user_id: int, days: int, now: dt.datetime) -> List[models.Expense]:
    since = now - dt.timedelta(days=days)
    return db.query(models.Expense).filter(
        models.Expense.user_id == user_id, models.Expense.timestamp >= since).all()


# -------------------------------------------------------------- round-up --

def roundup_savings(db: Session, user_id: int, step: int = 10, now: dt.datetime | None = None) -> Dict:
    now = now or dt.datetime.utcnow()
    step = step if step in (5, 10, 50, 100) else 10
    rows = _expenses(db, user_id, 90, now)
    if not rows:
        return {"available": False, "reason": tr("Log a few expenses to see how much spare change you could be saving.")}
    spare_each = []
    for e in rows:
        up = math.ceil(e.amount / step) * step
        spare_each.append(round(up - e.amount, 2))
    total_spare = round(sum(spare_each), 2)
    days_span = max((now - min(e.timestamp for e in rows)).days, 1)
    per_month = total_spare / days_span * 30.4
    by_week: Dict[str, float] = defaultdict(float)
    for e, s in zip(rows, spare_each):
        wk = (e.timestamp.date() - dt.timedelta(days=e.timestamp.weekday())).isoformat()
        by_week[wk] += s
    weeks = sorted(by_week.items())[-12:]
    return {
        "available": True, "step": step, "transactions": len(rows), "days": days_span,
        "total_spare": total_spare, "per_month": round(per_month, 2),
        "projected_year": round(per_month * 12, 2),
        "avg_per_purchase": round(total_spare / len(rows), 2),
        "weekly": [{"week": w, "amount": round(a, 2)} for w, a in weeks],
    }


# ------------------------------------------------------------- forecast --

def cashflow_forecast(db: Session, user: models.User, horizon: int = 14, now: dt.datetime | None = None) -> Dict:
    now = now or dt.datetime.utcnow()
    today = now.date()
    rows = _expenses(db, user.id, 84, now)
    if len(rows) < 10:
        return {"available": False, "reason": tr("A forecast needs about 10 expenses of history.")}

    recurring_items = recurring_svc.detect_recurring(
        db.query(models.Expense).filter(models.Expense.user_id == user.id).all(), today)
    recurring_merchants = {r["merchant"].lower() for r in recurring_items}

    # discretionary baseline by weekday: average per occurrence of that weekday, excluding recurring bills
    by_date: Dict[dt.date, float] = defaultdict(float)
    for e in rows:
        if (e.merchant or "").lower() not in recurring_merchants:
            by_date[e.timestamp.date()] += e.amount
    first = min(e.timestamp.date() for e in rows)
    wd_tot, wd_cnt = defaultdict(float), defaultdict(int)
    d = first
    while d <= today:
        wd_tot[d.weekday()] += by_date.get(d, 0.0)
        wd_cnt[d.weekday()] += 1
        d += dt.timedelta(days=1)
    wd_avg = {k: wd_tot[k] / max(wd_cnt[k], 1) for k in range(7)}

    days = []
    cum = 0.0
    # recurring charges expected inside the horizon
    due: Dict[dt.date, float] = defaultdict(float)
    for r in recurring_items:
        nd = dt.date.fromisoformat(r["next_expected"])
        step = {"weekly": 7, "fortnightly": 14, "monthly": 30, "quarterly": 91, "yearly": 365}[r["cadence"]]
        while nd <= today + dt.timedelta(days=horizon):
            if nd > today:
                due[nd] += r["typical_amount"]
            nd += dt.timedelta(days=step)
    for i in range(1, horizon + 1):
        day = today + dt.timedelta(days=i)
        base = wd_avg[day.weekday()]
        bills = due.get(day, 0.0)
        cum += base + bills
        days.append({"date": day.isoformat(), "expected": round(base + bills, 2),
                     "bills": round(bills, 2), "cumulative": round(cum, 2)})

    # compare with what's left of this month's spendable budget
    from . import pulse
    sts = pulse.safe_to_spend(db, user, now)
    left = sts.get("month_remaining") if sts.get("available") else None
    verdict, note = "unknown", tr("Add your monthly income in Settings to compare against a budget.")
    if left is not None:
        month_end = dt.date(today.year, today.month, 1) + dt.timedelta(days=32)
        month_end = month_end.replace(day=1) - dt.timedelta(days=1)
        in_month = [x for x in days if dt.date.fromisoformat(x["date"]) <= month_end]
        proj = in_month[-1]["cumulative"] if in_month else 0
        if proj > left:
            verdict = "over"
            note = tr("At your usual pace you'd run about {amount} over budget before month-end.", amount=round(proj - left))
        elif proj > 0.85 * left:
            verdict = "tight"
            note = tr("You'd finish the month with very little to spare — keep an eye on extras.")
        else:
            verdict = "safe"
            note = tr("On track — roughly {amount} of cushion left at month-end.", amount=round(left - proj))
    peak = max(days, key=lambda x: x["expected"])
    return {
        "available": True, "horizon": horizon, "days": days,
        "total_expected": days[-1]["cumulative"], "verdict": verdict, "note": note,
        "peak_day": peak, "bills_in_window": round(sum(due.values()), 2),
    }
