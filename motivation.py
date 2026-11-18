"""
Motivation Engine.

Everything here is derived from the signed-in user's actual data — logging
streaks come from real expense timestamps, badges are earned from real
counts (triggers found, goals set, interventions that measurably worked),
and the encouragement message references real numbers pulled from the
monthly report. Nothing is a static, hardcoded placeholder.
"""
from __future__ import annotations
import datetime as dt
from typing import List
from sqlalchemy.orm import Session

from .. import models
from ..i18n import N_, tr
from . import report_generator


def compute_streak(expenses: List[models.Expense], today: dt.date = None) -> int:
    """Counts consecutive days (ending today or the most recent logging day)
    that have at least one logged expense."""
    if not expenses:
        return 0
    today = today or dt.date.today()
    days_with_activity = {e.timestamp.date() for e in expenses}

    # Anchor the streak at the most recent activity day so a user who logged
    # yesterday but not yet today still sees their streak intact.
    anchor = max(days_with_activity)
    if (today - anchor).days > 1:
        return 0  # streak broken — more than a day has passed with no activity

    streak = 0
    cursor = anchor
    while cursor in days_with_activity:
        streak += 1
        cursor -= dt.timedelta(days=1)
    return streak


def compute_badges(db: Session, user: models.User, expenses: List[models.Expense], streak: int) -> List[dict]:
    trigger_count = db.query(models.Trigger).filter(models.Trigger.user_id == user.id).count()
    goal_count = db.query(models.Goal).filter(models.Goal.user_id == user.id).count()
    interventions = db.query(models.Intervention).filter(models.Intervention.user_id == user.id).all()
    working_intervention = any((i.effectiveness_pct or 0) <= -5 for i in interventions)
    completed_goal = any(g.saved_amount >= g.target_amount for g in
                          db.query(models.Goal).filter(models.Goal.user_id == user.id).all())

    scan_count = sum(1 for e in expenses if getattr(e, "source", "manual") == "scan")

    return [
        {
            "id": "first_steps", "label": N_("First Steps"), "icon": "🌱",
            "description": N_("Logged your first expense"),
            "earned": len(expenses) >= 1,
        },
        {
            "id": "consistent", "label": N_("Consistent Tracker"), "icon": "📒",
            "description": N_("Logged expenses on 10 or more occasions"),
            "earned": len(expenses) >= 10,
        },
        {
            "id": "dedicated", "label": N_("Dedicated Logger"), "icon": "📚",
            "description": N_("Logged expenses on 25 or more occasions"),
            "earned": len(expenses) >= 25,
        },
        {
            "id": "streak_3", "label": N_("3-Day Streak"), "icon": "🔥",
            "description": N_("Logged something 3 days in a row"),
            "earned": streak >= 3,
        },
        {
            "id": "streak_7", "label": N_("Week Warrior"), "icon": "⚡",
            "description": N_("Logged something 7 days in a row"),
            "earned": streak >= 7,
        },
        {
            "id": "pattern_spotter", "label": N_("Pattern Spotter"), "icon": "🔍",
            "description": N_("Discovered your first spending trigger"),
            "earned": trigger_count >= 1,
        },
        {
            "id": "pattern_master", "label": N_("Pattern Master"), "icon": "🧠",
            "description": N_("Discovered 5 or more spending triggers"),
            "earned": trigger_count >= 5,
        },
        {
            "id": "goal_setter", "label": N_("Goal Setter"), "icon": "🎯",
            "description": N_("Created a savings goal"),
            "earned": goal_count >= 1,
        },
        {
            "id": "goal_crusher", "label": N_("Goal Crusher"), "icon": "🏆",
            "description": N_("Fully funded a savings goal"),
            "earned": completed_goal,
        },
        {
            "id": "receipt_ninja", "label": N_("Receipt Ninja"), "icon": "📸",
            "description": N_("Scanned a bill and let the app fill in the expense"),
            "earned": scan_count >= 1,
        },
        {
            "id": "money_saver", "label": N_("Money Saver"), "icon": "💚",
            "description": N_("Had an intervention that measurably reduced spending"),
            "earned": working_intervention,
        },
    ]


# ---------------------------------------------------------------------------
# XP & Level system.
#
# Every point of XP traces back to something the user actually did — there
# is no random or cosmetic inflation. This turns the (already real) habit
# score, streak, badge count, and logging volume into a single progression
# number with friendly level titles, which is a stronger, more game-like
# throughline than showing four separate stats.
# ---------------------------------------------------------------------------
LEVELS = [
    (0, N_("Money Rookie")),
    (100, N_("Budget Beginner")),
    (220, N_("Smart Spender")),
    (360, N_("Savings Scout")),
    (520, N_("Habit Hacker")),
    (700, N_("Pattern Pro")),
    (900, N_("Goal Getter")),
    (1150, N_("Finance Whiz")),
    (1450, N_("Money Master")),
    (1800, N_("Legendary Saver")),
]


def compute_xp(habit_score: int, streak: int, badge_count: int, expense_count: int) -> int:
    return int(
        habit_score * 2
        + streak * 10
        + badge_count * 25
        + min(expense_count, 50) * 1
    )


def compute_level(xp: int) -> dict:
    level_index = 0
    for i, (threshold, _title) in enumerate(LEVELS):
        if xp >= threshold:
            level_index = i
        else:
            break

    level_number = level_index + 1
    title = LEVELS[level_index][1]
    current_threshold = LEVELS[level_index][0]

    if level_index + 1 < len(LEVELS):
        next_threshold = LEVELS[level_index + 1][0]
        xp_into_level = xp - current_threshold
        xp_for_next_level = next_threshold - current_threshold
    else:
        # max level reached — show it as "full" rather than dividing by zero
        xp_into_level = 1
        xp_for_next_level = 1

    return {
        "level": level_number,
        "level_title": tr(title),
        "xp": xp,
        "xp_into_level": xp_into_level,
        "xp_for_next_level": xp_for_next_level,
        "is_max_level": level_index + 1 >= len(LEVELS),
    }


def pick_message(habit_score: int, streak: int, pct_change: float, badges: List[dict]) -> str:
    new_badges = [b for b in badges if b["earned"]]

    if streak >= 7:
        return tr("{n}-day logging streak — that consistency is exactly what makes the trigger engine accurate!", n=streak)
    if streak >= 3:
        return tr("{n} days in a row logging expenses — keep it up, patterns get clearer the more data you add.", n=streak)
    if pct_change < -5:
        return tr("You're spending {pct}% less than your own 3-month average this month. Nice work.", pct=abs(round(pct_change)))
    if habit_score >= 80:
        return tr("Your financial habit score is {score}/100 — one of your strongest months yet.", score=habit_score)
    if len(new_badges) == 0:
        return tr("Log a few expenses to unlock your first badge and start building a streak.")
    return tr("You've earned {n} badge(s) so far. Keep logging to unlock more.", n=len(new_badges))


def get_motivation(db: Session, user: models.User) -> dict:
    expenses = db.query(models.Expense).filter(models.Expense.user_id == user.id).all()
    streak = compute_streak(expenses)
    badges = compute_badges(db, user, expenses, streak)
    earned_count = sum(1 for b in badges if b["earned"])

    report = report_generator.build_monthly_report(db, user.id)
    message = pick_message(
        report["financial_habit_score"], streak,
        report["self_comparison"]["pct_change_vs_baseline"], badges,
    )

    xp = compute_xp(report["financial_habit_score"], streak, earned_count, len(expenses))
    level_info = compute_level(xp)

    badges = [{**b, "label": tr(b["label"]), "description": tr(b["description"])} for b in badges]
    return {"streak_days": streak, "message": message, "badges": badges, **level_info}
