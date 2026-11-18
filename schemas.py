import datetime as dt
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator


FONT_STYLES = ("default", "clean", "rounded", "serif", "classic", "readable", "dyslexia", "mono")

# ---------- Auth ----------
class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str = Field(min_length=8)
    date_of_birth: Optional[dt.date] = None
    age: Optional[int] = Field(default=None, ge=1, le=120)  # fallback if no DOB
    platform_mode: Optional[str] = None  # kid/teen/adult, auto-computed if omitted
    monthly_income: float = 0.0
    current_savings: float = 0.0
    currency: str = "INR"
    language: str = "en"
    theme: str = "night"
    guardian_confirmed: bool = False


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    age: Optional[int] = None
    date_of_birth: Optional[dt.date] = None
    platform_mode: str
    should_prompt_adult_transition: bool = False
    should_prompt_senior_transition: bool = False
    monthly_income: float
    current_savings: float
    currency: str
    base_currency: str
    language: str
    theme: str
    font_scale: float = 1.0
    font_style: str = "default"
    line_spacing: str = "normal"


class UserUpdate(BaseModel):
    date_of_birth: Optional[dt.date] = None
    platform_mode: Optional[str] = None
    monthly_income: Optional[float] = None
    current_savings: Optional[float] = None
    currency: Optional[str] = None
    language: Optional[str] = None
    theme: Optional[str] = None
    font_scale: Optional[float] = Field(default=None, ge=0.75, le=1.75)
    font_style: Optional[str] = Field(default=None, pattern="^(" + "|".join(FONT_STYLES) + ")$")
    line_spacing: Optional[str] = Field(default=None, pattern="^(normal|relaxed)$")


class AdultTransitionResponse(BaseModel):
    user: UserOut
    guide: List[str]


class SeniorTransitionResponse(BaseModel):
    user: UserOut
    guide: List[str]


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------- Expenses ----------
class ExpenseCreate(BaseModel):
    amount: float = Field(gt=0)
    category: Optional[str] = None       # auto-categorized if omitted
    merchant: str = ""
    payment_method: str = "Other"
    note: str = ""
    timestamp: Optional[dt.datetime] = None
    location: str = ""
    device_usage: str = ""
    screen_time_minutes: int = 0
    source: str = Field(default="manual", pattern="^(manual|scan|quick)$")


class TextParseRequest(BaseModel):
    text: str = Field(min_length=1, max_length=20000)


class ReceiptParseRequest(BaseModel):
    text: str = Field(min_length=1, max_length=20000)
    # extra OCR passes of the same bill (differently pre-processed images)
    alt_texts: List[str] = Field(default_factory=list, max_length=4)


class ExpenseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    amount: float
    category: str
    merchant: str
    payment_method: str
    note: str
    timestamp: dt.datetime
    location: str
    device_usage: str
    screen_time_minutes: int
    source: Optional[str] = "manual"

    @field_validator("source", mode="before")
    @classmethod
    def _source_default(cls, v):
        return v or "manual"      # tolerate NULL in rows created before the column existed


# ---------- Goals ----------
class GoalCreate(BaseModel):
    title: str
    target_amount: float = Field(gt=0)
    saved_amount: float = 0.0
    deadline: dt.datetime


class GoalUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=300)
    target_amount: Optional[float] = Field(default=None, gt=0)
    deadline: Optional[dt.datetime] = None


class GoalContributionCreate(BaseModel):
    amount: float                       # positive = add money, negative = take money out
    note: str = Field(default="", max_length=200)


class GoalContributionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    amount: float
    note: str
    created_at: dt.datetime


class ExpenseUpdate(BaseModel):
    amount: Optional[float] = Field(default=None, gt=0)
    category: Optional[str] = None
    merchant: Optional[str] = None
    payment_method: Optional[str] = None
    note: Optional[str] = None
    timestamp: Optional[dt.datetime] = None


class GoalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    target_amount: float
    saved_amount: float
    deadline: dt.datetime


# ---------- Triggers / XAI ----------
class TriggerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    context_key: str
    category_affected: str
    description: str
    evidence: List[str]
    confidence: float
    occurrences: int
    active: bool


# ---------- Interventions ----------
class InterventionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    trigger_id: int
    intervention_type: str
    variant: str
    description: str
    status: str
    baseline_avg: float
    result_avg: Optional[float]
    effectiveness_pct: Optional[float]
    user_feedback: Optional[str]


class FeedbackIn(BaseModel):
    feedback: str = Field(pattern="^(up|down)$")


class CounterfactualRequest(BaseModel):
    category: str
    times_per_week_reduction: float = Field(ge=0)
    avg_amount_override: Optional[float] = None


# ---------- Help chatbot ----------
class HelpAskRequest(BaseModel):
    message: str = Field(min_length=1, max_length=500)


class HelpAskResponse(BaseModel):
    reply: str
    suggestions: List[str] = []


# ---------- Motivation ----------
class Badge(BaseModel):
    id: str
    label: str
    icon: str
    earned: bool
    description: str


class MotivationOut(BaseModel):
    streak_days: int
    message: str
    badges: List[Badge]
    level: int
    level_title: str
    xp: int
    xp_into_level: int
    xp_for_next_level: int
    is_max_level: bool


# ---------- Budgets / account / import ----------
class BudgetSet(BaseModel):
    monthly_limit: float = Field(gt=0, le=1e12)


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=200)


class AccountDelete(BaseModel):
    password: str


class CsvImport(BaseModel):
    csv_text: str = Field(min_length=1, max_length=5_000_000)
