"""
Subscription Radar -- recurring-charge detector.

Looks at the user's *own* history and finds merchants that charge on a
regular rhythm (weekly / monthly / quarterly / yearly) with a stable amount.
Every detection ships with the counted evidence behind it (how many charges,
what gaps, what amounts) so it follows the app's explain-everything rule.

Also flags "price creep": the latest charge is noticeably higher than the
earlier ones.
"""
from __future__ import annotations

import datetime as dt
import re
import statistics
from collections import defaultdict
from typing import Dict, List

from .. import models
from ..i18n import N_, tr

# (name, min_gap, max_gap, approx_days, charges_per_month)
CADENCES = [
    (N_("weekly"), 5, 9, 7, 52 / 12),
    (N_("fortnightly"), 12, 17, 14, 26 / 12),
    (N_("monthly"), 26, 35, 30.4, 1.0),
    (N_("quarterly"), 80, 100, 91, 1 / 3),
    (N_("yearly"), 340, 390, 365, 1 / 12),
]
SUBSCRIPTION_WORDS = ("netflix", "spotify", "prime", "hotstar", "youtube", "icloud", "google one",
                      "subscription", "membership", "gym", "broadband", "wifi", "insurance", "rent",
                      "emi", "recharge", "electricity")


def _norm(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (name or "").lower()).strip()


def detect_recurring(expenses: List[models.Expense], today: dt.date | None = None) -> List[Dict]:
    today = today or dt.date.today()
    groups: Dict[str, List[models.Expense]] = defaultdict(list)
    for e in expenses:
        key = _norm(e.merchant)
        if key:
            groups[key].append(e)

    results: List[Dict] = []
    for key, rows in groups.items():
        rows.sort(key=lambda r: r.timestamp)
        looks_like_sub = any(w in key for w in SUBSCRIPTION_WORDS)
        # Collapse same-day duplicates (one logical charge per day)
        by_day: Dict[dt.date, models.Expense] = {}
        for r in rows:
            by_day[r.timestamp.date()] = r
        rows = [by_day[d] for d in sorted(by_day)]
        if len(rows) < (2 if looks_like_sub else 3):
            continue

        gaps = [(rows[i + 1].timestamp.date() - rows[i].timestamp.date()).days for i in range(len(rows) - 1)]
        med_gap = statistics.median(gaps)
        cadence = next((c for c in CADENCES if c[1] <= med_gap <= c[2]), None)
        if not cadence:
            continue
        name, lo, hi, approx, per_month = cadence
        in_band = sum(1 for g in gaps if lo - 2 <= g <= hi + 2)
        regularity = in_band / len(gaps)
        if regularity < 0.7:
            continue

        amounts = [r.amount for r in rows]
        med_amt = statistics.median(amounts)
        if med_amt <= 0:
            continue
        spread = (max(amounts) - min(amounts)) / med_amt
        stable = sum(1 for a in amounts if abs(a - med_amt) <= 0.15 * med_amt) / len(amounts)
        if stable < 0.7:
            continue                      # varying amounts = habit, not subscription

        last = rows[-1]
        last_date = last.timestamp.date()
        next_due = last_date + dt.timedelta(days=round(approx))
        prior = amounts[:-1]
        creep = None
        if prior:
            base = statistics.median(prior)
            if base > 0 and (last.amount - base) / base >= 0.05:
                creep = round((last.amount - base) / base * 100, 1)

        confidence = round(min(0.99, 0.45 * regularity + 0.35 * stable + min(len(rows), 6) * 0.03 + (0.07 if looks_like_sub else 0)), 2)
        days_until = (next_due - today).days
        results.append({
            "merchant": last.merchant,
            "category": last.category,
            "cadence": name,
            "typical_amount": round(med_amt, 2),
            "last_amount": round(last.amount, 2),
            "occurrences": len(rows),
            "last_charged": last_date.isoformat(),
            "next_expected": next_due.isoformat(),
            "days_until_next": days_until,
            "overdue": days_until < -3,
            "monthly_cost": round(med_amt * per_month, 2),
            "annual_cost": round(med_amt * per_month * 12, 2),
            "price_creep_pct": creep,
            "confidence": confidence,
            "evidence": [
                tr("{n} charges found, median gap {gap} days ({cadence})", n=len(rows), gap=int(med_gap), cadence=tr(name)),
                tr("{pct}% of gaps fit the {cadence} rhythm", pct=int(regularity * 100), cadence=tr(name)),
                tr("{pct}% of amounts within 15% of {amount} (spread {spread}%)", pct=int(stable * 100), amount=round(med_amt, 2), spread=int(spread * 100)),
            ],
        })
    results.sort(key=lambda r: r["annual_cost"], reverse=True)
    return results
