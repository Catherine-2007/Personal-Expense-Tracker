"""
Family engine -- one app for the whole household.

Design rules
------------
* Everyone keeps their own account. A family only *links* accounts.
* Ranking rewards healthy HABITS (logging, streaks, no-spend days, spending
  below your own usual pace, goals, kudos) -- never "who spends the most" or
  "who spends the least". That keeps it fair between a 9-year-old and a parent.
* Privacy is per member (share_level): "full" (others see amounts and
  categories), "totals" (others see only the total) or "rank" (others see only
  points). Parents/owner always see children (role "child") so they can guide
  them.
* Amounts are converted to the VIEWER's base currency, so the frontend's
  normal money() display works unchanged.
* The API returns structured data (ids + parameters); the web app turns it
  into sentences in the reader's language.
"""
from __future__ import annotations

import datetime as dt
import secrets
from collections import defaultdict
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from .. import models
from ..i18n import N_, tr
from . import age_tier, fx_rates

SHARE_LEVELS = ("full", "totals", "rank")
ROLES = ("owner", "parent", "member", "child")
KUDOS_EMOJIS = ("👏", "🌟", "🔥", "💪", "🎉", "💚", "🐷", "🏆")
AVATARS = ("🙂", "😎", "🦊", "🐼", "🦁", "🐯", "🐸", "🦄", "🐧", "🐙", "🚀", "🌈", "🍀", "⚡", "🎨", "🧸")
CHALLENGE_KINDS = ("no_spend_days", "spend_cap", "log_days")
MAX_KUDOS_PER_DAY = 5
CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"   # no 0/O/1/I/L

# Titles are tiers of points. Marked for translation; the web app shows them with t().
TITLES = [
    (150, "Money Legend", "👑"),
    (100, "Budget Hero", "🦸"),
    (60, "Smart Saver", "🌟"),
    (30, "Rising Star", "🚀"),
    (0, "Getting Started", "🌱"),
]
[N_("Money Legend"), N_("Budget Hero"), N_("Smart Saver"), N_("Rising Star"), N_("Getting Started")]


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def new_invite_code(db: Session) -> str:
    while True:
        code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(6))
        if not db.query(models.Family).filter(models.Family.invite_code == code).first():
            return code


def get_membership(db: Session, user: models.User) -> Optional[models.FamilyMember]:
    return db.query(models.FamilyMember).filter(models.FamilyMember.user_id == user.id).first()


def is_parent(member: Optional[models.FamilyMember]) -> bool:
    return bool(member and member.role in ("owner", "parent"))


def _rate(rates: Dict[str, float], frm: str, to: str) -> float:
    if frm == to or not rates.get(frm) or not rates.get(to):
        return 1.0
    return rates[to] / rates[frm]


def _title_for(points: int) -> dict:
    for threshold, name, emoji in TITLES:
        if points >= threshold:
            return {"title": name, "emoji": emoji}
    return {"title": TITLES[-1][1], "emoji": TITLES[-1][2]}


def period_bounds(period: str, today: dt.date) -> tuple[dt.date, dt.date, dt.date, dt.date]:
    """(start, end, prev_start, prev_end) -- 'week' = last 7 days, 'month' = this calendar month."""
    if period == "week":
        start = today - dt.timedelta(days=6)
        return start, today, start - dt.timedelta(days=28), start - dt.timedelta(days=1)
    start = today.replace(day=1)
    prev_end = start - dt.timedelta(days=1)
    prev_start = (prev_end.replace(day=1) - dt.timedelta(days=62)).replace(day=1)
    return start, today, prev_start, prev_end


# ---------------------------------------------------------------------------
# per-member stats and points
# ---------------------------------------------------------------------------
def member_stats(db: Session, user: models.User, joined: dt.datetime, period: str,
                 today: dt.date, factor: float) -> dict:
    """All numbers for one person in one period, amounts multiplied by `factor`
    (currency conversion into the viewer's base currency)."""
    start, end, p_start, p_end = period_bounds(period, today)
    since = dt.datetime.combine(min(start, p_start), dt.time.min)
    rows = db.query(models.Expense).filter(
        models.Expense.user_id == user.id, models.Expense.timestamp >= since).all()

    by_day: Dict[dt.date, float] = defaultdict(float)
    cats: Dict[str, float] = defaultdict(float)
    scans = 0
    prev_total = 0.0
    count = 0
    for e in rows:
        d = e.timestamp.date()
        if d > end:
            continue
        if d >= start:
            by_day[d] += e.amount
            cats[e.category] += e.amount
            count += 1
            if getattr(e, "source", "manual") == "scan":
                scans += 1
        elif p_start <= d <= p_end:
            prev_total += e.amount

    total = sum(by_day.values())
    days_in_period = (end - start).days + 1
    # days that count for "no-spend": since the person joined (fair for newcomers)
    first_day = max(start, joined.date()) if joined else start
    countable_days = max((end - first_day).days + 1, 0)
    days_logged = len(by_day)
    # a no-spend day only counts for people who are actually using the app
    # (logged something in the last 30 days) -- otherwise "never logging" would win
    active = any(e.timestamp.date() >= today - dt.timedelta(days=30) for e in rows)
    no_spend_days = max(countable_days - len([d for d in by_day if d >= first_day]), 0) if active else 0

    # streak: consecutive days with a log, ending today (or yesterday: grace)
    all_days = {e.timestamp.date() for e in rows}
    cursor = today if today in all_days else today - dt.timedelta(days=1)
    streak = 0
    while cursor in all_days:
        streak += 1
        cursor -= dt.timedelta(days=1)

    # "usual" = average daily spend in the lookback window, scaled to the days elapsed so far
    prev_days = max((p_end - p_start).days + 1, 1)
    usual_to_date = prev_total / prev_days * days_in_period if prev_total > 0 else 0.0
    pace_change = ((usual_to_date - total) / usual_to_date) if usual_to_date > 0 else None   # >0 = spending less than usual

    goals = db.query(models.Goal).filter(models.Goal.user_id == user.id).all()
    goals_half = sum(1 for g in goals if g.target_amount and g.saved_amount / g.target_amount >= 0.5)
    goals_new = sum(1 for g in goals if g.created_at and g.created_at.date() >= start)

    # last 14 days sparkline
    spark = []
    for i in range(13, -1, -1):
        d = today - dt.timedelta(days=i)
        spark.append(round(sum(e.amount for e in rows if e.timestamp.date() == d) * factor, 2))
    top = max(cats.items(), key=lambda kv: kv[1]) if cats else None

    return {
        "total": round(total * factor, 2),
        "count": count,
        "days_logged": days_logged,
        "no_spend_days": no_spend_days,
        "streak": streak,
        "scans": scans,
        "goals_half": goals_half,
        "goals_new": goals_new,
        "pace_change": round(pace_change, 3) if pace_change is not None else None,
        "top_category": top[0] if top else None,
        "top_category_amount": round(top[1] * factor, 2) if top else 0.0,
        "categories": {k: round(v * factor, 2) for k, v in sorted(cats.items(), key=lambda kv: -kv[1])},
        "spark": spark,
        "days_in_period": days_in_period,
    }


def points_for(stats: dict, kudos_received: int, challenges_won: int) -> dict:
    """Transparent point breakdown. Every part is capped so nobody can 'farm' a win."""
    logging_pts = min(stats["days_logged"] * 2, 40)
    streak_pts = min(stats["streak"], 14) * 3
    no_spend_pts = min(stats["no_spend_days"] * 2, 20)
    pace = stats["pace_change"]
    pace_pts = round(min(max(pace, 0.0), 0.5) * 60) if pace is not None else 0      # up to 30
    goal_pts = min(stats["goals_half"] * 10, 20) + min(stats["goals_new"] * 5, 10)
    kudos_pts = min(kudos_received * 2, 20)
    scan_pts = min(stats["scans"], 10)
    challenge_pts = challenges_won * 10
    parts = {
        "logging": logging_pts, "streak": streak_pts, "no_spend": no_spend_pts, "pace": pace_pts,
        "goals": goal_pts, "kudos": kudos_pts, "scans": scan_pts, "challenges": challenge_pts,
    }
    return {"parts": parts, "total": sum(parts.values())}


# ---------------------------------------------------------------------------
# challenges
# ---------------------------------------------------------------------------
def challenge_progress(db: Session, ch: models.FamilyChallenge, members: List[models.FamilyMember],
                       factors: Dict[int, float], today: dt.date) -> dict:
    """Progress for one challenge, counted across the whole family."""
    start, end = ch.start_date, ch.end_date
    elapsed = max(min((today - start).days + 1, (end - start).days + 1), 0)
    length = (end - start).days + 1
    finished = today > end
    since = dt.datetime.combine(start, dt.time.min)
    until = dt.datetime.combine(end, dt.time.max)

    value = 0.0
    contributions = []
    members_ok = 0
    for m in members:
        rows = db.query(models.Expense).filter(
            models.Expense.user_id == m.user_id, models.Expense.timestamp >= since,
            models.Expense.timestamp <= until).all()
        days_with = {e.timestamp.date() for e in rows}
        if ch.kind == "no_spend_days":
            joined = m.joined_at.date() if m.joined_at else start
            first = max(start, joined)
            last = min(today, end)
            recent = db.query(models.Expense).filter(
                models.Expense.user_id == m.user_id,
                models.Expense.timestamp >= dt.datetime.combine(today - dt.timedelta(days=30), dt.time.min)).first()
            mine = max((last - first).days + 1 - len([d for d in days_with if first <= d <= last]), 0) \
                if (last >= first and recent) else 0
            value += mine
            contributions.append({"user_id": m.user_id, "value": mine})
        elif ch.kind == "spend_cap":
            spent = sum(e.amount for e in rows if not ch.category or e.category == ch.category) * factors.get(m.user_id, 1.0)
            value += spent
            contributions.append({"user_id": m.user_id, "value": round(spent, 2)})
        else:  # log_days -- everyone should log on `target` different days
            n = len(days_with)
            contributions.append({"user_id": m.user_id, "value": n})
            if n >= ch.target:
                members_ok += 1

    if ch.kind == "no_spend_days":
        done = value >= ch.target
        pct = min(value / ch.target, 1.0) if ch.target else 0
        state = "won" if done else ("lost" if finished else "active")
        shown = value
    elif ch.kind == "spend_cap":
        pace_ok = value <= ch.target * (elapsed / length if length else 1)
        pct = min(value / ch.target, 1.0) if ch.target else 0
        state = ("lost" if value > ch.target else "won") if finished else ("active" if value <= ch.target else "lost")
        shown = round(value, 2)
        return {"id": ch.id, "kind": ch.kind, "title": ch.title, "target": ch.target, "category": ch.category,
                "start_date": start.isoformat(), "end_date": end.isoformat(), "value": shown, "pct": round(pct, 3),
                "state": state, "on_pace": pace_ok, "days_left": max((end - today).days, 0),
                "contributions": contributions}
    else:
        total_members = max(len(members), 1)
        pct = members_ok / total_members
        done = members_ok == total_members
        state = "won" if done else ("lost" if finished else "active")
        shown = members_ok
    return {"id": ch.id, "kind": ch.kind, "title": ch.title, "target": ch.target, "category": ch.category,
            "start_date": start.isoformat(), "end_date": end.isoformat(), "value": shown, "pct": round(pct, 3),
            "state": state, "on_pace": True, "days_left": max((end - today).days, 0),
            "contributions": contributions}


# ---------------------------------------------------------------------------
# the big one: build the family dashboard for a viewer
# ---------------------------------------------------------------------------
def build_dashboard(db: Session, viewer: models.User, period: str = "month",
                    today: Optional[dt.date] = None) -> dict:
    today = today or dt.datetime.utcnow().date()
    me = get_membership(db, viewer)
    if me is None:
        return {"family": None}
    fam: models.Family = me.family
    rates = fx_rates.get_rates()["rates"]
    viewer_ccy = viewer.base_currency or "INR"
    members: List[models.FamilyMember] = list(fam.members)

    since_kudos = dt.datetime.combine(period_bounds(period, today)[0], dt.time.min)
    kudos_all = db.query(models.FamilyKudos).filter(models.FamilyKudos.family_id == fam.id).all()
    kudos_in = defaultdict(int)
    kudos_out = defaultdict(int)
    for k in kudos_all:
        if k.created_at >= since_kudos:
            kudos_in[k.to_user] += 1
            kudos_out[k.from_user] += 1

    factors = {m.user_id: _rate(rates, (m.user.base_currency or "INR"), viewer_ccy) for m in members}
    challenges = db.query(models.FamilyChallenge).filter(models.FamilyChallenge.family_id == fam.id) \
        .order_by(models.FamilyChallenge.end_date.desc()).all()
    chal_out = [challenge_progress(db, c, members, factors, today) for c in challenges]
    won_ids = [c for c in chal_out if c["state"] == "won"]

    rows = []
    for m in members:
        u = m.user
        st = member_stats(db, u, m.joined_at, period, today, factors[m.user_id])
        # challenges this member helped win (contributed > 0 / logged)
        mine_won = sum(1 for c in won_ids if any(x["user_id"] == u.id and x["value"] > 0 for x in c["contributions"]))
        pts = points_for(st, kudos_in[u.id], mine_won)
        # visibility for THIS viewer
        if u.id == viewer.id or (is_parent(me) and m.role == "child") or m.share_level == "full":
            level = "full"
        elif m.share_level == "totals":
            level = "totals"
        else:
            level = "rank"
        age = age_tier.compute_age(u)
        rows.append({
            "user_id": u.id, "member_id": m.id, "name": u.name, "avatar": m.avatar, "role": m.role,
            "age": age if (level == "full" or m.role == "child") else None,
            "managed": u.managed_by is not None,
            "is_me": u.id == viewer.id, "share_level": m.share_level, "visible": level,
            "points": pts["total"], "points_parts": pts["parts"],
            **_title_for(pts["total"]),
            "streak": st["streak"], "days_logged": st["days_logged"], "no_spend_days": st["no_spend_days"],
            "scans": st["scans"], "pace_change": st["pace_change"],
            "kudos_received": kudos_in[u.id], "kudos_sent": kudos_out[u.id],
            "total": st["total"] if level in ("full", "totals") else None,
            "count": st["count"] if level == "full" else None,
            "top_category": st["top_category"] if level == "full" else None,
            "categories": st["categories"] if level == "full" else None,
            "spark": st["spark"] if level in ("full", "totals") else None,
            "_goals": st["goals_half"] + st["goals_new"],
        })

    # rank (ties share a rank number, stable by name)
    rows.sort(key=lambda r: (-r["points"], r["name"].lower()))
    rank = 0
    last_pts = None
    for i, r in enumerate(rows):
        if r["points"] != last_pts:
            rank = i + 1
            last_pts = r["points"]
        r["rank"] = rank

    # awards (one winner each, only when someone really earned it)
    def best(key, minimum, rows_=rows):
        cand = [r for r in rows_ if (r.get(key) or 0) >= minimum]
        return max(cand, key=lambda r: (r[key], -r["rank"]))["user_id"] if cand else None
    improvers = [r for r in rows if r["pace_change"] is not None and r["pace_change"] > 0.02]
    awards = [
        {"id": "streak", "user_id": best("streak", 3)},
        {"id": "no_spend", "user_id": best("no_spend_days", 2)},
        {"id": "improver", "user_id": max(improvers, key=lambda r: r["pace_change"])["user_id"] if improvers else None},
        {"id": "goals", "user_id": best("_goals", 1)},
        {"id": "scanner", "user_id": best("scans", 1)},
        {"id": "cheer", "user_id": best("kudos_sent", 1)},
    ]
    awards = [a for a in awards if a["user_id"] is not None]
    for r in rows:
        r.pop("_goals", None)

    visible_total = sum(r["total"] for r in rows if r["total"] is not None)
    hidden = sum(1 for r in rows if r["total"] is None)
    family_budget = round(fam.monthly_budget * _rate(rates, fam.currency or "INR", viewer_ccy), 2) if fam.monthly_budget else 0.0

    # category split across members who share categories
    cat_totals: Dict[str, float] = defaultdict(float)
    for r in rows:
        for k, v in (r["categories"] or {}).items():
            cat_totals[k] += v
    top_cats = [{"category": k, "amount": round(v, 2)} for k, v in sorted(cat_totals.items(), key=lambda kv: -kv[1])[:5]]

    # activity feed: kudos + new members (structured; the app words them)
    names = {m.user_id: m.user.name for m in members}
    avatars = {m.user_id: m.avatar for m in members}
    feed = []
    for k in sorted(kudos_all, key=lambda x: x.created_at, reverse=True)[:12]:
        feed.append({"type": "kudos", "at": k.created_at.isoformat(), "emoji": k.emoji,
                     "from": names.get(k.from_user, "?"), "to": names.get(k.to_user, "?"),
                     "from_avatar": avatars.get(k.from_user, "🙂")})
    for m in sorted(members, key=lambda x: x.joined_at or dt.datetime.min, reverse=True)[:4]:
        feed.append({"type": "joined", "at": (m.joined_at or dt.datetime.utcnow()).isoformat(),
                     "name": m.user.name, "avatar": m.avatar})
    feed.sort(key=lambda x: x["at"], reverse=True)

    # kudos allowance left today for the viewer
    today_start = dt.datetime.combine(today, dt.time.min)
    sent_today = sum(1 for k in kudos_all if k.from_user == viewer.id and k.created_at >= today_start)

    return {
        "family": {
            "id": fam.id, "name": fam.name, "emoji": fam.emoji, "currency": viewer_ccy,
            "invite_code": fam.invite_code if is_parent(me) or me.role == "member" else None,
            "monthly_budget": family_budget, "created_at": fam.created_at.isoformat(),
        },
        "me": {"user_id": viewer.id, "role": me.role, "avatar": me.avatar, "share_level": me.share_level,
               "is_parent": is_parent(me), "kudos_left_today": max(MAX_KUDOS_PER_DAY - sent_today, 0)},
        "period": period,
        "members": rows,
        "totals": {"spent": round(visible_total, 2), "hidden_members": hidden,
                   "budget_used_pct": round(visible_total / family_budget, 3) if family_budget and period == "month" else None},
        "top_categories": top_cats,
        "awards": awards,
        "challenges": chal_out,
        "feed": feed[:14],
        "kudos_emojis": list(KUDOS_EMOJIS),
        "avatars": list(AVATARS),
    }
