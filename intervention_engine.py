"""
Intervention Engine + A/B Testing Module + Outcome Measurement.

For every active Trigger, this proposes a *personalized* behavioral nudge
drawn from four intervention archetypes (Habit / Delay / Limit / Friction),
deliberately alternates between two candidate archetypes across triggers
(A/B testing), and later measures whether the nudge actually reduced spend
by comparing a "before" baseline against an "after" outcome window -- the
closed loop Detect -> Explain -> Intervene -> Measure -> Learn -> Adapt.
"""
from __future__ import annotations
import datetime as dt
from typing import List, Optional
from sqlalchemy.orm import Session

from .. import models
from ..i18n import register_template

TEMPLATES = {
    # registered so the stored English text can be shown in the reader's language
    "Habit": register_template("Prepare a small snack / plan before {context} to short-circuit the {category} trigger."),
    "Delay": register_template("Apply a 24-hour rule: wait a day before any {category} purchase made during {context}."),
    "Limit": register_template("Set a soft budget cap for {category} spend that occurs during {context}."),
    "Friction": register_template("Switch to cash (instead of {payment}) for small {category} spends during {context} to add natural friction."),
}

# Which two archetypes we alternate between per category (drives the A/B test)
ARCHETYPE_PAIRS = {
    "Food": ("Habit", "Delay"),
    "Shopping": ("Delay", "Friction"),
    "Transport": ("Limit", "Habit"),
    "Entertainment": ("Limit", "Friction"),
}
DEFAULT_PAIR = ("Limit", "Friction")

MEASURE_WINDOW_DAYS = 14


def _pick_variant(db: Session, user_id: int) -> str:
    """Alternates A/B assignment so roughly half of new interventions test each arm."""
    count = db.query(models.Intervention).filter(models.Intervention.user_id == user_id).count()
    return "A" if count % 2 == 0 else "B"


def suggest_intervention(db: Session, user: models.User, trigger: models.Trigger,
                          expenses_in_context: List[models.Expense]) -> models.Intervention:
    existing = (
        db.query(models.Intervention)
        .filter(models.Intervention.trigger_id == trigger.id, models.Intervention.status != "stopped")
        .first()
    )
    if existing:
        return existing

    pair = ARCHETYPE_PAIRS.get(trigger.category_affected, DEFAULT_PAIR)
    variant = _pick_variant(db, user.id)
    archetype = pair[0] if variant == "A" else pair[1]

    payment = expenses_in_context[0].payment_method if expenses_in_context else "digital payment"
    context_readable = trigger.context_key.replace("+", ", ").lower()
    description = TEMPLATES[archetype].format(
        context=context_readable, category=trigger.category_affected, payment=payment
    )

    baseline_avg = (
        sum(e.amount for e in expenses_in_context) / len(expenses_in_context)
        if expenses_in_context else 0.0
    )

    row = models.Intervention(
        user_id=user.id,
        trigger_id=trigger.id,
        intervention_type=archetype,
        variant=variant,
        description=description,
        status="testing",
        baseline_avg=round(baseline_avg, 2),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def measure_effectiveness(db: Session, intervention: models.Intervention) -> models.Intervention:
    """Compares spend on the trigger's category in the window since the
    intervention was created (post) against its baseline (pre)."""
    cutoff = intervention.created_at
    trigger = intervention.trigger
    post_expenses = (
        db.query(models.Expense)
        .filter(
            models.Expense.user_id == intervention.user_id,
            models.Expense.category == trigger.category_affected,
            models.Expense.timestamp >= cutoff,
            models.Expense.timestamp <= cutoff + dt.timedelta(days=MEASURE_WINDOW_DAYS),
        )
        .all()
    )
    if not post_expenses or intervention.baseline_avg == 0:
        return intervention

    result_avg = sum(e.amount for e in post_expenses) / len(post_expenses)
    effectiveness = ((result_avg - intervention.baseline_avg) / intervention.baseline_avg) * 100

    intervention.result_avg = round(result_avg, 2)
    intervention.effectiveness_pct = round(effectiveness, 1)
    intervention.status = "active" if effectiveness <= -5 else (
        "stopped" if effectiveness >= 10 else "testing"
    )
    db.commit()
    db.refresh(intervention)
    return intervention


def submit_feedback(db: Session, intervention: models.Intervention, feedback: str) -> models.Intervention:
    """Human-feedback learning loop (infographic block 6): a 'down' vote
    immediately retires the intervention so it isn't shown again as-is."""
    intervention.user_feedback = feedback
    if feedback == "down":
        intervention.status = "stopped"
    db.commit()
    db.refresh(intervention)
    return intervention
