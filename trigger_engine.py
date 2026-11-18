"""
Spending Trigger Confidence Engine (core novel component).

Unlike a plain "category totals" tracker, this module mines a user's own
expense history for CONTEXT -> CATEGORY associations (e.g. "late-night +
weekday" -> "Food"), attaches a statistical confidence score AND a bundle
of human-readable evidence to every pattern it surfaces, and continuously
decays / expires patterns that stop recurring.

Pipeline (mirrors "Detect -> Explain -> Intervene -> Measure -> Learn ->
Adapt"):
    1. build_context_fingerprint(expense)   -> tags every expense with a
       reproducible context vector (time bucket, day type, payment method)
    2. discover_triggers(expenses)          -> weighted conditional-
       probability mining over the context vectors, with a recency-decay
       half-life so older behaviour matters less than recent behaviour
    3. persist_triggers(db, user, triggers) -> upserts Trigger rows,
       expiring ones that have not recurred recently (pattern expiration)

This is intentionally dependency-free (no external ML libraries) so the
project runs anywhere, while still being a genuine statistical model that
can be swapped for a heavier ML backend later without changing callers.
"""
from __future__ import annotations

import json
import math
import datetime as dt
from collections import defaultdict
from typing import List, Dict, Tuple

from sqlalchemy.orm import Session

from .. import models
from ..i18n import register_template

# --- tunables -------------------------------------------------------------
EV_SIMILAR = register_template("{n} of {total} similar transactions in this context were '{category}'")
EV_AFTER_9PM = register_template("{n} occurred after 9 PM")
EV_CONSISTENT = register_template("Consistently logged during {period} hours")
EV_WEEKS = register_template("Pattern repeated across {n} distinct week(s)")
TRIGGER_DESC = register_template("You tend to spend on {category} during {context} periods")

MIN_OCCURRENCES = 3          # a context/category pair needs >= this many raw hits
MIN_CONFIDENCE = 0.5         # conditional probability threshold to call it a "trigger"
DECAY_HALFLIFE_DAYS = 30.0   # recency weighting half-life
EXPIRE_AFTER_DAYS = 45       # no recurrence in this window -> pattern marked inactive


def _time_bucket(ts: dt.datetime) -> str:
    h = ts.hour
    if h >= 22 or h < 3:
        return "Late Night"
    if 3 <= h < 11:
        return "Morning"
    if 11 <= h < 17:
        return "Afternoon"
    return "Evening"


def _day_type(ts: dt.datetime) -> str:
    return "Weekend" if ts.weekday() >= 5 else "Weekday"


def build_context_fingerprint(expense: models.Expense) -> Dict[str, str]:
    """Creates the reproducible context vector shown in infographic block 2.1."""
    return {
        "time_bucket": _time_bucket(expense.timestamp),
        "day_type": _day_type(expense.timestamp),
        "payment_method": expense.payment_method or "Other",
        "high_screen_time": "High" if (expense.screen_time_minutes or 0) >= 30 else "Low",
    }


def _decay_weight(age_days: float) -> float:
    return math.pow(0.5, age_days / DECAY_HALFLIFE_DAYS)


def discover_triggers(expenses: List[models.Expense], now: dt.datetime = None) -> List[dict]:
    """
    Mines (context -> category) conditional probabilities across all of the
    user's expenses. Returns candidate trigger dicts (not yet persisted).
    """
    now = now or dt.datetime.utcnow()
    if not expenses:
        return []

    # weighted counts: context_key -> total weight ; (context_key, category) -> weight
    context_totals: Dict[str, float] = defaultdict(float)
    context_raw_totals: Dict[str, int] = defaultdict(int)
    pair_totals: Dict[Tuple[str, str], float] = defaultdict(float)
    pair_raw_count: Dict[Tuple[str, str], int] = defaultdict(int)
    pair_examples: Dict[Tuple[str, str], List[models.Expense]] = defaultdict(list)
    pair_weeks: Dict[Tuple[str, str], set] = defaultdict(set)
    pair_last_seen: Dict[Tuple[str, str], dt.datetime] = {}

    for exp in expenses:
        fp = build_context_fingerprint(exp)
        # two granularities of context: (time_bucket + day_type) is the primary,
        # human-readable trigger context used in the UI.
        context_key = f"{fp['time_bucket']}+{fp['day_type']}"
        age_days = max((now - exp.timestamp).days, 0)
        w = _decay_weight(age_days)

        context_totals[context_key] += w
        context_raw_totals[context_key] += 1
        pair = (context_key, exp.category)
        pair_totals[pair] += w
        pair_raw_count[pair] += 1
        pair_examples[pair].append(exp)
        pair_weeks[pair].add(exp.timestamp.isocalendar()[1])
        if pair not in pair_last_seen or exp.timestamp > pair_last_seen[pair]:
            pair_last_seen[pair] = exp.timestamp

    triggers = []
    for (context_key, category), weight in pair_totals.items():
        raw_count = pair_raw_count[(context_key, category)]
        if raw_count < MIN_OCCURRENCES:
            continue
        confidence = weight / context_totals[context_key]
        if confidence < MIN_CONFIDENCE:
            continue

        examples = pair_examples[(context_key, category)]
        after_9pm = sum(1 for e in examples if e.timestamp.hour >= 21 or e.timestamp.hour < 3)
        distinct_weeks = len(pair_weeks[(context_key, category)])
        last_seen = pair_last_seen[(context_key, category)]

        # stored in English; translated at read time via tr_stored() (see i18n.py)
        evidence = [
            EV_SIMILAR.format(n=raw_count, total=context_raw_totals[context_key], category=category),
            EV_AFTER_9PM.format(n=after_9pm) if after_9pm else
            EV_CONSISTENT.format(period=context_key.split('+')[0].lower()),
            EV_WEEKS.format(n=distinct_weeks),
        ]

        triggers.append({
            "context_key": context_key,
            "category_affected": category,
            "description": TRIGGER_DESC.format(category=category, context=context_key.replace('+', ', ').lower()),
            "evidence": evidence,
            "confidence": round(min(confidence, 0.99), 2),
            "occurrences": raw_count,
            "last_seen": last_seen,
        })

    # strongest patterns first
    triggers.sort(key=lambda t: (t["confidence"], t["occurrences"]), reverse=True)
    return triggers


def persist_triggers(db: Session, user_id: int, candidates: List[dict], now: dt.datetime = None) -> List[models.Trigger]:
    """Upserts discovered triggers and expires ones that stopped recurring."""
    now = now or dt.datetime.utcnow()
    existing = {
        (t.context_key, t.category_affected): t
        for t in db.query(models.Trigger).filter(models.Trigger.user_id == user_id).all()
    }
    seen_keys = set()
    result = []

    for c in candidates:
        key = (c["context_key"], c["category_affected"])
        seen_keys.add(key)
        row = existing.get(key)
        if row:
            row.confidence = c["confidence"]
            row.occurrences = c["occurrences"]
            row.evidence_json = json.dumps(c["evidence"])
            row.last_seen = c["last_seen"]
            row.active = True
        else:
            row = models.Trigger(
                user_id=user_id,
                context_key=c["context_key"],
                category_affected=c["category_affected"],
                description=c["description"],
                evidence_json=json.dumps(c["evidence"]),
                confidence=c["confidence"],
                occurrences=c["occurrences"],
                last_seen=c["last_seen"],
                first_seen=now,
                active=True,
            )
            db.add(row)
        result.append(row)

    # pattern expiration (infographic block 2.7): fade out triggers that
    # no longer appear in the freshly-mined candidate set and haven't
    # recurred within EXPIRE_AFTER_DAYS
    for key, row in existing.items():
        if key not in seen_keys:
            age = (now - row.last_seen).days if row.last_seen else 9999
            if age > EXPIRE_AFTER_DAYS:
                row.active = False

    db.commit()
    for row in result:
        db.refresh(row)
    return result
