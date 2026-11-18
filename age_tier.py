"""
Age-tier platform logic.

The app offers four experience tiers, each with a genuinely different UI
(not just a color theme):

  - "kid"    (under 13)  — simplest wording, big buttons, extra encouragement
  - "teen"   (13-17)     — full features with more guidance/tooltips
  - "adult"  (18-59)     — the complete, unrestricted experience
  - "senior" (60+)       — larger text, higher contrast, simplified single-
                            column layout, calmer motion — built for
                            readability and confidence, not simplification
                            of content (seniors get the full detail, just
                            presented more accessibly)

Age is computed from date_of_birth whenever available (accurate, and lets
the app notice real birthdays/milestones) and falls back to the static
`age` field entered at signup otherwise.
"""
from __future__ import annotations
import datetime as dt
from typing import Optional

from .. import models
from ..i18n import N_

TIER_KID = "kid"
TIER_TEEN = "teen"
TIER_ADULT = "adult"
TIER_SENIOR = "senior"

SENIOR_AGE_THRESHOLD = 60


def compute_age(user: models.User, today: Optional[dt.date] = None) -> Optional[int]:
    today = today or dt.date.today()
    if user.date_of_birth:
        dob = user.date_of_birth
        years = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        return max(years, 0)
    if user.age is not None:
        return user.age
    return None


def tier_for_age(age: Optional[int]) -> str:
    if age is None:
        return TIER_ADULT  # default to the full experience if age is unknown
    if age < 13:
        return TIER_KID
    if age < 18:
        return TIER_TEEN
    if age < SENIOR_AGE_THRESHOLD:
        return TIER_ADULT
    return TIER_SENIOR


def should_prompt_adult_transition(user: models.User, today: Optional[dt.date] = None) -> bool:
    """Fires once when a kid/teen account's real age reaches 18."""
    age = compute_age(user, today)
    if age is None or age < 18 or age >= SENIOR_AGE_THRESHOLD:
        return False
    return user.platform_mode not in (TIER_ADULT, TIER_SENIOR) and not user.adult_transition_prompted


def should_prompt_senior_transition(user: models.User, today: Optional[dt.date] = None) -> bool:
    """Fires once when an account's real age reaches the senior threshold."""
    age = compute_age(user, today)
    if age is None or age < SENIOR_AGE_THRESHOLD:
        return False
    return user.platform_mode != TIER_SENIOR and not user.senior_transition_prompted


ADULT_TRANSITION_GUIDE = [
    N_("The wording across the app is now the full, direct version instead of the simplified one."),
    N_("Trigger and intervention details now show full statistical evidence and effectiveness numbers."),
    N_("You now have access to every theme and every currency without restriction."),
    N_("Your existing data, goals, and history all carry over exactly as they were — nothing is reset."),
]

SENIOR_TRANSITION_GUIDE = [
    N_("Text throughout the app is now larger and higher-contrast, without losing any detail or features."),
    N_("The Comfort theme is applied automatically — you can still change it any time in Settings."),
    N_("Layouts are simplified to a single readable column rather than dense multi-column grids."),
    N_("Animation is gentler and slower, reducing visual clutter while keeping the app feeling alive."),
    N_("Your existing data, goals, and history all carry over exactly as they were — nothing is reset."),
]
