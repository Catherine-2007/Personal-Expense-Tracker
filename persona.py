"""
Spending Persona -- a plain-language "type" from the last 90 days, shown with
the numbers that earned it. Rule-based and explainable; never judgemental --
every persona comes with a constructive tip.
"""
from __future__ import annotations

import datetime as dt
import statistics
from collections import defaultdict
from typing import Dict

from sqlalchemy.orm import Session

from .. import models
from ..i18n import N_, tr

PERSONAS = {
    "night_owl": (N_("Night Owl Nibbler"), "🦉", N_("Your best (and priciest) ideas arrive after dark."),
                  N_("Try a 'sleep on it' rule: put late-night orders on a wishlist and decide in the morning.")),
    "weekend": (N_("Weekend Warrior"), "🎉", N_("Weekdays are disciplined; weekends are for living."),
                N_("Set a fixed weekend budget on Friday, then enjoy it guilt-free.")),
    "planner": (N_("Steady Planner"), "🧭", N_("Calm, regular and in control."),
                N_("You're primed to automate savings — move a fixed amount on payday.")),
    "foodie": (N_("Foodie Explorer"), "🍜", N_("Your wallet follows your taste buds."),
               N_("Batch-cook two days a week or set a monthly food cap to keep the fun without the creep.")),
    "sprinter": (N_("Impulse Sprinter"), "⚡", N_("Lots of quick, small buys that add up fast."),
                 N_("Use a 24-hour pause on anything non-essential and watch the small stuff shrink.")),
    "big_ticket": (N_("Big-Ticket Hunter"), "🎯", N_("A few large purchases drive most of your spending."),
                   N_("Plan big buys with a sinking fund so they never surprise your month.")),
    "balanced": (N_("Balanced Navigator"), "⚖️", N_("A healthy mix — no single habit dominates."),
                 N_("Pick one category to trim by 10% for a month and bank the difference.")),
}


def build_persona(db: Session, user_id: int, now: dt.datetime | None = None) -> Dict:
    now = now or dt.datetime.utcnow()
    since = now - dt.timedelta(days=90)
    rows = db.query(models.Expense).filter(
        models.Expense.user_id == user_id, models.Expense.timestamp >= since).all()
    if len(rows) < 12:
        return {"available": False, "have": len(rows), "need": 12,
                "reason": tr("Log about 12+ expenses (a few weeks) to reveal your spending persona.")}

    total = sum(e.amount for e in rows) or 1.0
    night = sum(e.amount for e in rows if e.timestamp.hour >= 22 or e.timestamp.hour < 4) / total
    weekend = sum(e.amount for e in rows if e.timestamp.weekday() >= 5) / total
    by_cat = defaultdict(float)
    for e in rows:
        by_cat[e.category] += e.amount
    top_cat, top_amt = max(by_cat.items(), key=lambda kv: kv[1])
    food_share = by_cat.get("Food", 0) / total
    amounts = sorted((e.amount for e in rows), reverse=True)
    top10 = sum(amounts[: max(1, len(amounts) // 10)]) / total
    med = statistics.median(amounts)
    small_share = sum(1 for a in amounts if a <= med * 0.6) / len(amounts)
    days_span = max((now - since).days, 1)
    active_days = len({e.timestamp.date() for e in rows})
    no_spend_ratio = 1 - active_days / days_span
    daily = defaultdict(float)
    for e in rows:
        daily[e.timestamp.date()] += e.amount
    dvals = list(daily.values())
    cv = (statistics.pstdev(dvals) / statistics.mean(dvals)) if len(dvals) > 1 and statistics.mean(dvals) else 1.0
    per_day = len(rows) / max(active_days, 1)

    scores = {
        "night_owl": night / 0.25,
        "weekend": ((weekend - 2 / 7) / 0.2 + 1) if weekend > 0.45 else 0,
        "foodie": food_share / 0.4,
        "sprinter": (per_day / 3.5) if (small_share > 0.45 and per_day >= 2.5) else 0,
        "big_ticket": top10 / 0.5,
        "planner": (1.0 + (0.6 - min(cv, 0.6))) if (cv < 0.6 and no_spend_ratio > 0.2) else 0,
    }
    key, best = max(scores.items(), key=lambda kv: kv[1])
    if best < 1.0:
        key = "balanced"
    name, emoji, tagline, tip = PERSONAS[key]
    name, tagline, tip = tr(name), tr(tagline), tr(tip)
    pct = lambda x: round(x * 100)  # noqa: E731
    traits = [
        {"label": tr("After-dark spending"), "value": pct(night), "detail": tr("of spend between 10pm and 4am")},
        {"label": tr("Weekend share"), "value": pct(weekend), "detail": tr("of spend on Sat/Sun (an even split ≈ 29%)")},
        {"label": tr("Top category: {category}", category=tr(top_cat)), "value": pct(top_amt / total), "detail": tr("of everything you spent")},
        {"label": tr("Big purchases"), "value": pct(top10), "detail": tr("of spend from your top 10% of purchases")},
        {"label": tr("No-spend days"), "value": pct(no_spend_ratio), "detail": tr("of the last {days} days", days=days_span)},
    ]
    return {"available": True, "id": key, "name": name, "emoji": emoji, "tagline": tagline, "tip": tip,
            "traits": traits, "based_on": len(rows), "window_days": days_span}
