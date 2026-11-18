from fastapi import APIRouter, Depends, HTTPException, status
from ..i18n import tr
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..security import hash_password, verify_password, create_access_token
from ..deps import get_current_user
from ..services import age_tier

router = APIRouter(prefix="/auth", tags=["auth"])


def build_user_out(user: models.User) -> schemas.UserOut:
    computed_age = age_tier.compute_age(user)
    return schemas.UserOut(
        id=user.id,
        name=user.name,
        email=user.email,
        age=computed_age,
        date_of_birth=user.date_of_birth,
        platform_mode=user.platform_mode or "adult",
        should_prompt_adult_transition=age_tier.should_prompt_adult_transition(user),
        should_prompt_senior_transition=age_tier.should_prompt_senior_transition(user),
        monthly_income=user.monthly_income,
        current_savings=user.current_savings,
        currency=user.currency,
        base_currency=user.base_currency,
        language=user.language,
        theme=user.theme,
        font_scale=user.font_scale or 1.0,
        font_style=user.font_style or "default",
        line_spacing=user.line_spacing or "normal",
    )


@router.post("/register", response_model=schemas.Token, status_code=status.HTTP_201_CREATED)
def register(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    if db.query(models.User).filter(models.User.email == payload.email).first():
        raise HTTPException(status_code=400, detail=tr("Email already registered"))

    user = models.User(
        name=payload.name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        age=payload.age,
        date_of_birth=payload.date_of_birth,
        monthly_income=payload.monthly_income,
        current_savings=payload.current_savings,
        currency=payload.currency or "INR",
        base_currency=payload.currency or "INR",  # amounts are entered in whatever currency was chosen at signup, permanently
        language=payload.language or "en",
        theme=payload.theme or "night",
        guardian_confirmed=payload.guardian_confirmed,
    )

    # Determine the platform experience tier: explicit choice wins, otherwise
    # auto-computed from age/date of birth (defaults to "adult" if unknown).
    computed_age = age_tier.compute_age(user)
    user.platform_mode = payload.platform_mode or age_tier.tier_for_age(computed_age)

    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(subject=user.email)
    return schemas.Token(access_token=token, user=build_user_out(user))


@router.post("/login", response_model=schemas.Token)
def login(payload: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail=tr("Incorrect email or password"))
    token = create_access_token(subject=user.email)
    return schemas.Token(access_token=token, user=build_user_out(user))


@router.get("/me", response_model=schemas.UserOut)
def me(current_user: models.User = Depends(get_current_user)):
    return build_user_out(current_user)


@router.patch("/me", response_model=schemas.UserOut)
def update_me(
    payload: schemas.UserUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(current_user, field, value)
    db.commit()
    db.refresh(current_user)
    return build_user_out(current_user)


@router.post("/transition-to-adult", response_model=schemas.AdultTransitionResponse)
def transition_to_adult(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Called when the user accepts the 'you're 18 now' prompt: switches
    them to the full, unrestricted adult experience and returns a short
    guide explaining what changed."""
    current_user.platform_mode = "adult"
    current_user.adult_transition_prompted = True
    db.commit()
    db.refresh(current_user)
    return schemas.AdultTransitionResponse(
        user=build_user_out(current_user),
        guide=[tr(g) for g in age_tier.ADULT_TRANSITION_GUIDE],
    )


@router.post("/dismiss-adult-prompt", response_model=schemas.UserOut)
def dismiss_adult_prompt(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Called when the user picks 'not now' — stops asking again without
    changing their current platform mode."""
    current_user.adult_transition_prompted = True
    db.commit()
    db.refresh(current_user)
    return build_user_out(current_user)


@router.post("/transition-to-senior", response_model=schemas.SeniorTransitionResponse)
def transition_to_senior(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Called when the user accepts the 'switch to Comfort mode' prompt at
    60: switches to the senior-tier experience (larger text, higher
    contrast, simplified layout) and returns a short guide."""
    current_user.platform_mode = "senior"
    current_user.senior_transition_prompted = True
    if current_user.theme not in ("senior",):
        current_user.theme = "senior"
    db.commit()
    db.refresh(current_user)
    return schemas.SeniorTransitionResponse(
        user=build_user_out(current_user),
        guide=[tr(g) for g in age_tier.SENIOR_TRANSITION_GUIDE],
    )


@router.post("/dismiss-senior-prompt", response_model=schemas.UserOut)
def dismiss_senior_prompt(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Called when the user picks 'not now' for the Comfort-mode prompt."""
    current_user.senior_transition_prompted = True
    db.commit()
    db.refresh(current_user)
    return build_user_out(current_user)


@router.post("/change-password", status_code=204)
def change_password(payload: schemas.PasswordChange, db: Session = Depends(get_db),
                    current_user: models.User = Depends(get_current_user)):
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail=tr("Your current password is incorrect."))
    current_user.password_hash = hash_password(payload.new_password)
    db.commit()
    return None


@router.post("/delete-account", status_code=204)
def delete_account(payload: schemas.AccountDelete, db: Session = Depends(get_db),
                   current_user: models.User = Depends(get_current_user)):
    """Permanently removes the account and everything in it (expenses, goals, budgets, family membership)."""
    if not verify_password(payload.password, current_user.password_hash):
        raise HTTPException(status_code=400, detail=tr("Your current password is incorrect."))
    uid = current_user.id
    m = db.query(models.FamilyMember).filter(models.FamilyMember.user_id == uid).first()
    if m:
        fam_ = m.family
        others = [x for x in fam_.members if x.user_id != uid]
        if not others:
            db.delete(fam_)                     # last member: the family goes with them
        else:
            heir = next((x for x in others if x.role == "parent"), None) or \
                next((x for x in others if x.role == "member"), None) or others[0]
            if m.role == "owner":
                heir.role = "owner"
            for c in db.query(models.FamilyChallenge).filter(models.FamilyChallenge.created_by == uid):
                c.created_by = heir.user_id
            if fam_.created_by == uid:
                fam_.created_by = heir.user_id
            db.delete(m)
    db.query(models.FamilyKudos).filter((models.FamilyKudos.from_user == uid) | (models.FamilyKudos.to_user == uid)).delete(synchronize_session=False)
    db.query(models.Budget).filter(models.Budget.user_id == uid).delete(synchronize_session=False)
    db.flush()
    db.delete(db.get(models.User, uid))
    db.commit()
    return None
