"""
Report & Insight generator.

Bundles several of the "unique features" from the infographic's block 3
into one monthly-report payload:

  - Self-comparison (personal baseline): this month vs the user's own
    trailing 3-month average, never vs other people.
  - What-Changed detector: category deltas month-over-month, with a
    plain-language reason pulled from active triggers when available.
  - Goal Conflict detector: required monthly savings rate for an active
    goal vs. actual savings rate -> a monthly gap.
  - Financial Habit Score: single composite 0-100 score.
"""
from __future__ import annotations
import calendar
import datetime as dt
from collections import defaultdict
from typing import List
from sqlalchemy.orm import Session

from .. import models
from ..i18n import tr, month_year


def _month_bounds(ref: dt.datetime):
    start = ref.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_day = calendar.monthrange(ref.year, ref.month)[1]
    end = start.replace(day=last_day, hour=23, minute=59, second=59)
    return start, end


def _category_totals(expenses: List[models.Expense]) -> dict:
    totals = defaultdict(float)
    for e in expenses:
        totals[e.category] += e.amount
    return dict(totals)


def self_comparison(db: Session, user_id: int, now: dt.datetime = None) -> dict:
    now = now or dt.datetime.utcnow()
    this_start, this_end = _month_bounds(now)
    baseline_start = (this_start - dt.timedelta(days=90))

    this_month = (
        db.query(models.Expense)
        .filter(models.Expense.user_id == user_id, models.Expense.timestamp >= this_start,
                models.Expense.timestamp <= this_end)
        .all()
    )
    prior_3mo = (
        db.query(models.Expense)
        .filter(models.Expense.user_id == user_id, models.Expense.timestamp >= baseline_start,
                models.Expense.timestamp < this_start)
        .all()
    )
    this_total = sum(e.amount for e in this_month)
    baseline_avg = (sum(e.amount for e in prior_3mo) / 3.0) if prior_3mo else 0.0
    pct_change = ((this_total - baseline_avg) / baseline_avg * 100) if baseline_avg else 0.0

    return {
        "this_month_total": round(this_total, 2),
        "personal_baseline_avg": round(baseline_avg, 2),
        "pct_change_vs_baseline": round(pct_change, 1),
    }


def what_changed(db: Session, user_id: int, now: dt.datetime = None) -> List[dict]:
    now = now or dt.datetime.utcnow()
    this_start, this_end = _month_bounds(now)
    last_month_ref = (this_start - dt.timedelta(days=1))
    last_start, last_end = _month_bounds(last_month_ref)

    this_month = (
        db.query(models.Expense)
        .filter(models.Expense.user_id == user_id, models.Expense.timestamp >= this_start,
                models.Expense.timestamp <= this_end).all()
    )
    last_month = (
        db.query(models.Expense)
        .filter(models.Expense.user_id == user_id, models.Expense.timestamp >= last_start,
                models.Expense.timestamp <= last_end).all()
    )
    this_totals = _category_totals(this_month)
    last_totals = _category_totals(last_month)

    active_triggers = {
        t.category_affected: t
        for t in db.query(models.Trigger).filter(models.Trigger.user_id == user_id, models.Trigger.active == True).all()
    }

    categories = set(this_totals) | set(last_totals)
    changes = []
    for cat in categories:
        cur = this_totals.get(cat, 0.0)
        prev = last_totals.get(cat, 0.0)
        delta = cur - prev
        if abs(delta) < 1:
            continue
        reason = None
        trig = active_triggers.get(cat)
        if trig:
            reason = tr("Linked to your '{context}' spending pattern ({pct}% confidence).",
                        context=", ".join(tr(p) for p in trig.context_key.split("+")), pct=int(trig.confidence * 100))
        changes.append({
            "category": cat,
            "this_month": round(cur, 2),
            "last_month": round(prev, 2),
            "change": round(delta, 2),
            "direction": "increased" if delta > 0 else "decreased",
            "reason": reason,
        })
    changes.sort(key=lambda c: abs(c["change"]), reverse=True)
    return changes


def goal_conflicts(db: Session, user_id: int, now: dt.datetime = None) -> List[dict]:
    now = now or dt.datetime.utcnow()
    goals = db.query(models.Goal).filter(models.Goal.user_id == user_id).all()
    results = []
    for g in goals:
        months_left = max((g.deadline.year - now.year) * 12 + (g.deadline.month - now.month), 1)
        remaining = max(g.target_amount - g.saved_amount, 0.0)
        required_monthly = remaining / months_left

        this_start, this_end = _month_bounds(now)
        this_month_spend = sum(
            e.amount for e in db.query(models.Expense).filter(
                models.Expense.user_id == user_id, models.Expense.timestamp >= this_start,
                models.Expense.timestamp <= this_end).all()
        )
        # crude actual-saving-rate proxy: income - spend, if income known
        user = db.query(models.User).get(user_id)
        actual_monthly_saving = max((user.monthly_income or 0) - this_month_spend, 0.0)
        gap = required_monthly - actual_monthly_saving

        results.append({
            "goal": g.title,
            "target_amount": g.target_amount,
            "months_left": months_left,
            "required_monthly_saving": round(required_monthly, 2),
            "actual_monthly_saving": round(actual_monthly_saving, 2),
            "monthly_gap": round(gap, 2),
            "at_risk": gap > 0,
        })
    return results


def financial_habit_score(self_cmp: dict, changes: List[dict], goal_status: List[dict]) -> int:
    score = 74  # neutral baseline, matches infographic's "Good" default
    # Cap this factor's influence so one unusually skewed month (e.g. a
    # short history relative to the current month) can't single-handedly
    # zero out the whole score.
    score -= min(max(self_cmp["pct_change_vs_baseline"], 0), 80) * 0.5
    score -= sum(1 for c in changes if c["direction"] == "increased") * 2
    score -= sum(5 for g in goal_status if g["at_risk"])
    score += sum(1 for c in changes if c["direction"] == "decreased")
    return int(max(0, min(100, round(score))))


def build_monthly_report(db: Session, user_id: int, now: dt.datetime = None) -> dict:
    now = now or dt.datetime.utcnow()
    this_start, this_end = _month_bounds(now)
    this_month = (
        db.query(models.Expense)
        .filter(models.Expense.user_id == user_id, models.Expense.timestamp >= this_start,
                models.Expense.timestamp <= this_end).all()
    )
    totals_by_cat = _category_totals(this_month)
    total_spend = sum(totals_by_cat.values())
    by_category_pct = {
        cat: round((amt / total_spend) * 100, 1) if total_spend else 0.0
        for cat, amt in totals_by_cat.items()
    }

    cmp_ = self_comparison(db, user_id, now)
    changes = what_changed(db, user_id, now)
    goals_status = goal_conflicts(db, user_id, now)
    score = financial_habit_score(cmp_, changes, goals_status)

    top_increase = next((c for c in changes if c["direction"] == "increased"), None)
    story = (
        tr("{category} spending increased {amount} vs last month.", category=tr(top_increase["category"]),
           amount=f"{abs(top_increase['change']):.0f}") + " " + (top_increase["reason"] or "")
    ) if top_increase else tr("Spending stayed roughly consistent with last month across categories.")

    return {
        "period": month_year(this_start),
        "total_spend": round(total_spend, 2),
        "by_category": totals_by_cat,
        "by_category_pct": by_category_pct,
        "self_comparison": cmp_,
        "what_changed": changes,
        "goal_status": goals_status,
        "financial_habit_score": score,
        "monthly_story": story,
    }
