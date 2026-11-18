"""
Generates demo users with realistic history so every feature — trigger
mining, XAI, interventions, motivation streaks/badges, and the age-tiered
platform experience — has something meaningful to show on first run.

Run from the backend/ directory:
    python seed_data.py
"""
import datetime as dt
import random

from app.database import SessionLocal, Base, engine, run_lightweight_migrations
from app import models
from app.security import hash_password
from app.services.categorizer import categorize
from app.services import age_tier

Base.metadata.create_all(bind=engine)
run_lightweight_migrations()   # adds newer columns (e.g. expenses.source) to older databases
db = SessionLocal()

DEMO_EMAIL = "demo@spendsense.app"
TEEN_EMAIL = "teen@spendsense.app"

existing = db.query(models.User).filter(models.User.email == DEMO_EMAIL).first()
if existing:
    print(f"Demo user already exists: {DEMO_EMAIL} / demo1234")
else:
    now = dt.datetime.utcnow()
    dob = now.date().replace(year=now.year - 24)  # exactly 24 years old

    user = models.User(
        name="Demo User",
        email=DEMO_EMAIL,
        password_hash=hash_password("demo1234"),
        monthly_income=45000,
        date_of_birth=dob,
    )
    user.platform_mode = age_tier.tier_for_age(age_tier.compute_age(user))
    db.add(user)
    db.commit()
    db.refresh(user)

    random.seed(42)

    def add(days_ago, hour, merchant, amount, payment="UPI", note="", screen_time=0):
        ts = (now - dt.timedelta(days=days_ago)).replace(hour=hour, minute=random.randint(0, 59))
        db.add(models.Expense(
            user_id=user.id, amount=amount, category=categorize(merchant, note),
            merchant=merchant, payment_method=payment, note=note, timestamp=ts,
            location="Home", screen_time_minutes=screen_time,
        ))

    # --- pattern: late-night food delivery on study/weekday nights ---
    for w in range(12):
        for _ in range(random.choice([1, 1, 2])):
            add(days_ago=w * 7 + random.randint(0, 4), hour=random.choice([22, 23, 0, 1]),
                merchant=random.choice(["Swiggy", "Zomato", "Dominos"]),
                amount=round(random.uniform(250, 650), 2), payment="UPI",
                note="late night order", screen_time=random.randint(30, 90))

    # --- regular groceries (weekly, daytime, low variance) ---
    for w in range(12):
        add(days_ago=w * 7 + 2, hour=11, merchant="BigBasket",
            amount=round(random.uniform(800, 1400), 2), payment="Card")

    # --- transport, weekday mornings ---
    for d in range(60):
        if random.random() < 0.4:
            add(days_ago=d, hour=random.choice([8, 9, 18, 19]), merchant="Uber",
                amount=round(random.uniform(80, 300), 2), payment="UPI")

    # --- occasional shopping ---
    for _ in range(8):
        add(days_ago=random.randint(0, 85), hour=random.choice([13, 20, 22]),
            merchant=random.choice(["Amazon", "Myntra"]),
            amount=round(random.uniform(500, 3200), 2), payment="Card")

    # --- bills, fixed monthly ---
    for m in range(3):
        add(days_ago=m * 30 + 1, hour=10, merchant="Electricity Board",
            amount=round(random.uniform(1200, 1800), 2), payment="Bank")

    db.commit()

    goal = models.Goal(
        user_id=user.id, title="Buy Laptop", target_amount=60000, saved_amount=18000,
        deadline=now + dt.timedelta(days=180),
    )
    db.add(goal)
    db.commit()

    print(f"Seeded demo user: {DEMO_EMAIL} / demo1234")

# --- recurring subscriptions for the demo user (powers Subscription Radar).
# Idempotent: only added once, and also back-fills databases seeded earlier.
_demo = db.query(models.User).filter(models.User.email == DEMO_EMAIL).first()
if _demo and not db.query(models.Expense).filter(
        models.Expense.user_id == _demo.id, models.Expense.merchant == "Netflix").first():
    _now = dt.datetime.utcnow()
    for _m in range(4):
        for _name, _amt, _day_offset, _pay in [("Netflix", 649.0, 3, "Card"), ("Spotify", 119.0, 9, "UPI"), ("Cult Gym", 1500.0, 14, "UPI")]:
            # Spotify gets a price rise on the latest charge to demo "price creep"
            _amount = 139.0 if (_name == "Spotify" and _m == 0) else _amt
            _ts = (_now - dt.timedelta(days=_m * 30 + _day_offset)).replace(hour=9, minute=30, second=0, microsecond=0)
            db.add(models.Expense(user_id=_demo.id, amount=_amount, category=categorize(_name, ""),
                                  merchant=_name, payment_method=_pay, note="subscription", timestamp=_ts))
    db.commit()
    print("Added demo subscriptions (Netflix, Spotify, Cult Gym).")

# --- let the trigger engine mine the demo user's history so the XAI pages and
# dashboard are populated on first run (idempotent).
from app.services import trigger_engine  # noqa: E402
_d = db.query(models.User).filter(models.User.email == DEMO_EMAIL).first()
if _d and db.query(models.Trigger).filter(models.Trigger.user_id == _d.id).count() == 0:
    _rows = db.query(models.Expense).filter(models.Expense.user_id == _d.id).all()
    _found = trigger_engine.persist_triggers(db, _d.id, trigger_engine.discover_triggers(_rows))
    print(f"Mined {len(_found)} spending triggers for the demo user.")

# --- a second account: just turned 18, still in "teen" platform mode, so
# you can see and test the birthday-transition prompt immediately. ---
teen_existing = db.query(models.User).filter(models.User.email == TEEN_EMAIL).first()
if teen_existing:
    print(f"Teen demo user already exists: {TEEN_EMAIL} / demo1234")
else:
    now = dt.datetime.utcnow()
    just_turned_18 = now.date().replace(year=now.year - 18) - dt.timedelta(days=3)  # birthday ~3 days ago
    teen_user = models.User(
        name="Alex (turned 18)",
        email=TEEN_EMAIL,
        password_hash=hash_password("demo1234"),
        monthly_income=8000,
        date_of_birth=just_turned_18,
        platform_mode="teen",  # deliberately stale, so the app will prompt to switch
        theme="kid",
        current_savings=1500,
    )
    db.add(teen_user)
    db.commit()
    db.refresh(teen_user)

    for w in range(4):
        ts = (now - dt.timedelta(days=w * 7 + 1)).replace(hour=13, minute=0)
        db.add(models.Expense(
            user_id=teen_user.id, amount=round(random.uniform(100, 400), 2),
            category=categorize("Zomato", ""), merchant="Zomato",
            payment_method="UPI", timestamp=ts,
        ))
    db.commit()
    print(f"Seeded teen (just turned 18) demo user: {TEEN_EMAIL} / demo1234")

# --- a third account: a kid-mode account with a savings goal, so the
# Playground dashboard (piggy bank, stars, badges) has something to show. ---
KID_EMAIL = "kid@spendsense.app"
kid_existing = db.query(models.User).filter(models.User.email == KID_EMAIL).first()
if kid_existing:
    print(f"Kid demo user already exists: {KID_EMAIL} / demo1234")
else:
    now = dt.datetime.utcnow()
    kid_dob = now.date().replace(year=now.year - 10)  # exactly 10 years old
    kid_user = models.User(
        name="Sam",
        email=KID_EMAIL,
        password_hash=hash_password("demo1234"),
        date_of_birth=kid_dob,
        platform_mode="kid",
        theme="kid",
        currency="USD",
        base_currency="USD",  # amounts below are authored as USD-scale figures
        current_savings=32,
        guardian_confirmed=True,
    )
    db.add(kid_user)
    db.commit()
    db.refresh(kid_user)

    for w in range(3):
        for _ in range(random.choice([1, 2])):
            ts = (now - dt.timedelta(days=w * 3 + random.randint(0, 2))).replace(hour=16, minute=0)
            db.add(models.Expense(
                user_id=kid_user.id, amount=round(random.uniform(2, 12), 2),
                category=categorize("Snack Shop", "candy"), merchant="Snack Shop",
                payment_method="Cash", timestamp=ts,
            ))
    db.add(models.Goal(
        user_id=kid_user.id, title="New Bike", target_amount=120, saved_amount=32,
        deadline=now + dt.timedelta(days=60),
    ))
    db.commit()
    print(f"Seeded kid demo user: {KID_EMAIL} / demo1234")

# --- a fourth account: a senior citizen ("Comfort mode") account with a
# few months of history, so the accessible large-text dashboard has real
# data to show. ---
SENIOR_EMAIL = "senior@spendsense.app"
senior_existing = db.query(models.User).filter(models.User.email == SENIOR_EMAIL).first()
if senior_existing:
    print(f"Senior demo user already exists: {SENIOR_EMAIL} / demo1234")
else:
    now = dt.datetime.utcnow()
    senior_dob = now.date().replace(year=now.year - 68)  # exactly 68 years old
    senior_user = models.User(
        name="Margaret",
        email=SENIOR_EMAIL,
        password_hash=hash_password("demo1234"),
        monthly_income=32000,
        current_savings=210000,
        date_of_birth=senior_dob,
        platform_mode="senior",
        theme="senior",
    )
    db.add(senior_user)
    db.commit()
    db.refresh(senior_user)

    for w in range(13):
        ts = (now - dt.timedelta(days=w * 7 + 2)).replace(hour=10, minute=0)
        db.add(models.Expense(
            user_id=senior_user.id, amount=round(random.uniform(600, 1400), 2),
            category=categorize("Pharmacy", "medicine"), merchant="Pharmacy",
            payment_method="Card", timestamp=ts,
        ))
        ts2 = (now - dt.timedelta(days=w * 7)).replace(hour=11, minute=0)
        db.add(models.Expense(
            user_id=senior_user.id, amount=round(random.uniform(900, 1800), 2),
            category=categorize("BigBasket", "groceries"), merchant="BigBasket",
            payment_method="Card", timestamp=ts2,
        ))
    db.add(models.Goal(
        user_id=senior_user.id, title="Home Repairs", target_amount=50000, saved_amount=21000,
        deadline=now + dt.timedelta(days=150),
    ))
    db.commit()
    print(f"Seeded senior demo user: {SENIOR_EMAIL} / demo1234")

db.close()
