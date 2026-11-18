import datetime as dt
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Date, ForeignKey, Boolean, Text
)
from sqlalchemy.orm import relationship
from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    monthly_income = Column(Float, default=0.0)
    current_savings = Column(Float, default=0.0)
    age = Column(Integer, nullable=True)               # fallback if no DOB given
    date_of_birth = Column(Date, nullable=True)          # preferred: lets the app track birthdays
    platform_mode = Column(String(20), default="adult")      # kid / teen / adult experience
    adult_transition_prompted = Column(Boolean, default=False)
    senior_transition_prompted = Column(Boolean, default=False)
    currency = Column(String(10), default="INR")          # ISO 4217 code (display preference)
    base_currency = Column(String(10), default="INR")     # currency amounts were actually entered in (immutable)
    language = Column(String(10), default="en")            # UI language code
    theme = Column(String(20), default="night")            # persisted theme choice
    font_scale = Column(Float, default=1.0)                # text size multiplier (0.75 - 1.75)
    font_style = Column(String(30), default="default")     # one of schemas.FONT_STYLES
    line_spacing = Column(String(10), default="normal")    # normal / relaxed
    guardian_confirmed = Column(Boolean, default=False)  # for under-13 users
    managed_by = Column(Integer, nullable=True)           # parent user id for family "child profiles" (no own login)
    created_at = Column(DateTime, default=dt.datetime.utcnow)

    expenses = relationship("Expense", back_populates="owner", cascade="all, delete-orphan")
    goals = relationship("Goal", back_populates="owner", cascade="all, delete-orphan")
    triggers = relationship("Trigger", back_populates="owner", cascade="all, delete-orphan")
    interventions = relationship("Intervention", back_populates="owner", cascade="all, delete-orphan")


class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    amount = Column(Float, nullable=False)
    category = Column(String(100), nullable=False, default="Uncategorized")
    merchant = Column(String(200), default="")
    payment_method = Column(String(30), default="Other")   # UPI, Card, Cash, Wallet, Bank
    note = Column(String(500), default="")
    source = Column(String(20), default="manual")           # manual / scan / quick

    # --- context fingerprint fields (see infographic block 2.1) ---
    timestamp = Column(DateTime, default=dt.datetime.utcnow, index=True)
    location = Column(String(200), default="")
    device_usage = Column(String(20), default="")           # e.g. "High", "Low"
    screen_time_minutes = Column(Integer, default=0)

    created_at = Column(DateTime, default=dt.datetime.utcnow)

    owner = relationship("User", back_populates="expenses")


class Goal(Base):
    __tablename__ = "goals"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    title = Column(String(300), nullable=False)
    target_amount = Column(Float, nullable=False)
    saved_amount = Column(Float, default=0.0)
    deadline = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=dt.datetime.utcnow)

    owner = relationship("User", back_populates="goals")
    contributions = relationship("GoalContribution", cascade="all, delete-orphan", order_by="GoalContribution.created_at.desc()")


class GoalContribution(Base):
    """One deposit (+) or withdrawal (-) on a savings goal -- gives each goal a history."""
    __tablename__ = "goal_contributions"

    id = Column(Integer, primary_key=True, index=True)
    goal_id = Column(Integer, ForeignKey("goals.id"), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    note = Column(String(200), default="")
    created_at = Column(DateTime, default=dt.datetime.utcnow)


class Trigger(Base):
    """A discovered spending-behavior pattern with statistical evidence (block 2.2 / 2.3)."""
    __tablename__ = "triggers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    context_key = Column(String(100), nullable=False)     # e.g. "late_night+weekday"
    category_affected = Column(String(100), nullable=False)
    description = Column(String(500), nullable=False)
    evidence_json = Column(Text, nullable=False)      # JSON list of evidence strings
    confidence = Column(Float, nullable=False)        # 0..1
    occurrences = Column(Integer, default=0)
    last_seen = Column(DateTime, default=dt.datetime.utcnow)
    first_seen = Column(DateTime, default=dt.datetime.utcnow)
    active = Column(Boolean, default=True)            # false once "expired" (2.7 pattern expiration)

    owner = relationship("User", back_populates="triggers")
    interventions = relationship("Intervention", back_populates="trigger", cascade="all, delete-orphan")


class Intervention(Base):
    """A suggested behavioral nudge tied to a Trigger, with A/B testing + outcome tracking."""
    __tablename__ = "interventions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    trigger_id = Column(Integer, ForeignKey("triggers.id"), nullable=False)

    intervention_type = Column(String(30), nullable=False)  # Habit / Delay / Limit / Friction
    variant = Column(String(5), default="A")                # A/B testing arm
    description = Column(String(500), nullable=False)
    status = Column(String(20), default="testing")            # testing / active / stopped
    baseline_avg = Column(Float, default=0.0)
    result_avg = Column(Float, nullable=True)
    effectiveness_pct = Column(Float, nullable=True)      # negative = spend reduced
    user_feedback = Column(String(10), nullable=True)         # up / down / null
    created_at = Column(DateTime, default=dt.datetime.utcnow)

    owner = relationship("User", back_populates="interventions")
    trigger = relationship("Trigger", back_populates="interventions")


# ---------------------------------------------------------------------------
# Family: one app, many people. Each person keeps their own account and data;
# a Family only links accounts together and adds shared views (leaderboard,
# challenges, kudos). What others can see is controlled per member.
# ---------------------------------------------------------------------------
class Family(Base):
    __tablename__ = "families"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    emoji = Column(String(10), default="🏡")
    invite_code = Column(String(12), unique=True, index=True, nullable=False)
    monthly_budget = Column(Float, default=0.0)           # optional shared budget (owner's base currency)
    currency = Column(String(10), default="INR")          # currency family totals are shown in
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=dt.datetime.utcnow)

    members = relationship("FamilyMember", back_populates="family", cascade="all, delete-orphan")
    challenges = relationship("FamilyChallenge", back_populates="family", cascade="all, delete-orphan")


class FamilyMember(Base):
    __tablename__ = "family_members"

    id = Column(Integer, primary_key=True, index=True)
    family_id = Column(Integer, ForeignKey("families.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)   # one family per person
    role = Column(String(10), default="member")           # owner / parent / member / child
    avatar = Column(String(10), default="🙂")
    share_level = Column(String(10), default="full")      # full / totals / rank
    joined_at = Column(DateTime, default=dt.datetime.utcnow)

    family = relationship("Family", back_populates="members")
    user = relationship("User")


class FamilyChallenge(Base):
    __tablename__ = "family_challenges"

    id = Column(Integer, primary_key=True, index=True)
    family_id = Column(Integer, ForeignKey("families.id"), nullable=False, index=True)
    kind = Column(String(20), nullable=False)             # no_spend_days / spend_cap / log_days
    title = Column(String(200), default="")
    target = Column(Float, nullable=False)                # days, or amount for spend_cap
    category = Column(String(100), default="")            # optional, for spend_cap
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=dt.datetime.utcnow)

    family = relationship("Family", back_populates="challenges")


class FamilyKudos(Base):
    __tablename__ = "family_kudos"

    id = Column(Integer, primary_key=True, index=True)
    family_id = Column(Integer, ForeignKey("families.id"), nullable=False, index=True)
    from_user = Column(Integer, ForeignKey("users.id"), nullable=False)
    to_user = Column(Integer, ForeignKey("users.id"), nullable=False)
    emoji = Column(String(10), default="👏")
    created_at = Column(DateTime, default=dt.datetime.utcnow)


class Budget(Base):
    """Monthly spending limit. category == "ALL" is the overall monthly budget."""
    __tablename__ = "budgets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    category = Column(String(60), nullable=False)
    monthly_limit = Column(Float, nullable=False)
    created_at = Column(DateTime, default=dt.datetime.utcnow)
