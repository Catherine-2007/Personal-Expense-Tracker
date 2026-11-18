"""
Start-up helpers that keep the database healthy and the demo accounts fresh.

* ensure_demo_data(): if the database has no users, seed the demo accounts so
  demo@spendsense.app / demo1234 always works. Disable with AUTO_SEED=0.
* rebase_demo_dates(): demo history is generated relative to the day it was
  seeded, so weeks later "this month" looks empty. If a demo account's newest
  expense is >2 days old its whole timeline is shifted so it ends today. Only
  accounts ending in @spendsense.app are touched -- never real users.
"""
import datetime as dt
import os
import runpy
import sys

from sqlalchemy.orm import Session

from . import models
from .database import BACKEND_DIR, SessionLocal

DEMO_SUFFIX = "@spendsense.app"


def ensure_demo_data() -> bool:
    if os.getenv("AUTO_SEED", "1") in ("0", "false", "False"):
        return False
    db = SessionLocal()
    try:
        if db.query(models.User).count() > 0:
            return False
    finally:
        db.close()
    if str(BACKEND_DIR) not in sys.path:
        sys.path.insert(0, str(BACKEND_DIR))
    runpy.run_path(str(BACKEND_DIR / "seed_data.py"), run_name="__seed__")
    return True


def rebase_demo_dates(db: Session | None = None, now: dt.datetime | None = None) -> int:
    own = db is None
    db = db or SessionLocal()
    now = now or dt.datetime.utcnow()
    shifted = 0
    try:
        for u in db.query(models.User).filter(models.User.email.like(f"%{DEMO_SUFFIX}")).all():
            newest = db.query(models.Expense.timestamp).filter(models.Expense.user_id == u.id) \
                .order_by(models.Expense.timestamp.desc()).first()
            if not newest or not newest[0]:
                continue
            gap = now - newest[0]
            if gap < dt.timedelta(days=2):
                continue
            delta = gap - dt.timedelta(hours=3)
            for e in db.query(models.Expense).filter(models.Expense.user_id == u.id):
                e.timestamp = e.timestamp + delta
            for g in db.query(models.Goal).filter(models.Goal.user_id == u.id):
                if g.deadline:
                    g.deadline = g.deadline + delta
            for t in db.query(models.Trigger).filter(models.Trigger.user_id == u.id):
                for attr in ("last_seen", "first_seen"):
                    v = getattr(t, attr, None)
                    if v:
                        setattr(t, attr, v + delta)
            for i in db.query(models.Intervention).filter(models.Intervention.user_id == u.id):
                if getattr(i, "created_at", None):
                    i.created_at = i.created_at + delta
            shifted += 1
        db.commit()
    finally:
        if own:
            db.close()
    return shifted


def ensure_demo_family() -> bool:
    """Creates a demo family (the four demo accounts + one child profile) the
    first time it is needed, so the Family page has something to show.
    Skipped if any family already exists or the demo accounts are missing."""
    import secrets
    from .security import hash_password
    from .services import family as fam

    db = SessionLocal()
    try:
        if db.query(models.Family).count() > 0:
            return False
        users = {u.email: u for u in db.query(models.User).filter(models.User.email.like(f"%{DEMO_SUFFIX}")).all()}
        owner = users.get("demo@spendsense.app")
        if owner is None:
            return False
        f = models.Family(name="The Demo Family", emoji="🏡", monthly_budget=0.0,
                          currency=owner.base_currency or "INR", invite_code="DEMO42", created_by=owner.id)
        db.add(f)
        db.flush()
        plan = [  # email, role, avatar, share level
            ("demo@spendsense.app", "owner", "😎", "full"),
            ("teen@spendsense.app", "member", "🦊", "totals"),
            ("kid@spendsense.app", "child", "🐼", "full"),
            ("senior@spendsense.app", "member", "🦁", "full"),
        ]
        member_ids = {}
        for email, role, avatar, level in plan:
            u = users.get(email)
            if u is None:
                continue
            db.add(models.FamilyMember(family_id=f.id, user_id=u.id, role=role, avatar=avatar, share_level=level,
                                       joined_at=dt.datetime.utcnow() - dt.timedelta(days=40)))
            member_ids[email] = u.id

        # one child profile managed by the owner (parent can switch into it)
        child = models.User(
            name="Aarav", email="aarav@kids.spendsense.app", password_hash=hash_password(secrets.token_urlsafe(24)),
            age=8, platform_mode="kid", currency=owner.currency, base_currency=owner.base_currency,
            language=owner.language, theme="kid", guardian_confirmed=True, managed_by=owner.id)
        db.add(child)
        db.flush()
        db.add(models.FamilyMember(family_id=f.id, user_id=child.id, role="child", avatar="🧸",
                                   joined_at=dt.datetime.utcnow() - dt.timedelta(days=30)))
        now = dt.datetime.utcnow()
        for days_ago, merchant, amount, cat in [(1, "School canteen", 40, "Food"), (2, "Toy shop", 150, "Shopping"),
                                                (4, "Ice cream", 60, "Food"), (5, "School canteen", 40, "Food"),
                                                (7, "Comic book", 120, "Entertainment"), (9, "School canteen", 40, "Food"),
                                                (16, "Stationery", 90, "Shopping"), (24, "Ice cream", 60, "Food")]:
            db.add(models.Expense(user_id=child.id, amount=amount, category=cat, merchant=merchant,
                                  payment_method="Cash", timestamp=now - dt.timedelta(days=days_ago, hours=3), source="manual"))
        db.add(models.Goal(user_id=child.id, title="New bicycle", target_amount=4000, saved_amount=1800,
                           deadline=now + dt.timedelta(days=90)))

        ids = list(member_ids.values()) + [child.id]
        for a, b, e in [(0, 1, "👏"), (1, 0, "🔥"), (3, 2, "🌟"), (0, 4, "🏆"), (2, 0, "💚")]:
            if a < len(ids) and b < len(ids):
                db.add(models.FamilyKudos(family_id=f.id, from_user=ids[a], to_user=ids[b], emoji=e,
                                          created_at=now - dt.timedelta(hours=2 + a + b)))
        today = now.date()
        db.add(models.FamilyChallenge(family_id=f.id, kind="no_spend_days", title="No-spend days", target=12,
                                      start_date=today - dt.timedelta(days=2), end_date=today + dt.timedelta(days=4),
                                      created_by=owner.id))
        db.add(models.FamilyChallenge(family_id=f.id, kind="log_days", title="", target=5,
                                      start_date=today - dt.timedelta(days=3), end_date=today + dt.timedelta(days=3),
                                      created_by=owner.id))
        db.commit()
        return True
    finally:
        db.close()
