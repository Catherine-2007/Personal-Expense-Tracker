"""
Explainable AI (XAI) layer.

Converts a Trigger's raw statistical evidence into a human-readable
explanation, always grounded in the evidence array (never a bare
assertion) -- this is what separates the tool from a black-box tracker:
every claim is traceable back to counted evidence and a confidence score.
"""
from __future__ import annotations
import json
from .. import models
from ..i18n import N_, tr, tr_stored

WHY_IT_MATTERS_TEMPLATES = {
    "Food": N_("Impulse or convenience-driven food spend tends to compound quietly -- small orders add up faster than planned purchases."),
    "Shopping": N_("Context-driven shopping (e.g. late-night browsing) bypasses the deliberation that daytime purchases usually get."),
    "Transport": N_("Repeated ad-hoc transport spend often signals a missing routine (e.g. no fixed commute plan) rather than one-off need."),
    "Entertainment": N_("Entertainment spend clustered in a context is usually a mood or boredom response rather than planned leisure budget."),
    "default": N_("Spending that clusters around a specific context is more habitual than deliberate, which makes it a good target for a small nudge."),
}


def explain_trigger(trigger: models.Trigger) -> dict:
    evidence = [tr_stored(e) for e in json.loads(trigger.evidence_json)]
    why = tr(WHY_IT_MATTERS_TEMPLATES.get(trigger.category_affected, WHY_IT_MATTERS_TEMPLATES["default"]))

    headline = tr(
        "You spend more on {category} during {context} periods.",
        category=tr(trigger.category_affected),
        context=" + ".join(tr(p) for p in trigger.context_key.split("+")),
    )
    seen_in = tr("This pattern is seen in {pct}% of similar cases.", pct=int(trigger.confidence * 100))

    return {
        "headline": headline,
        "evidence": evidence,
        "confidence": trigger.confidence,
        "seen_in": seen_in,
        "why_it_matters": why,
    }
