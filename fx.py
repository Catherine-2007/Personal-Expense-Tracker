from fastapi import APIRouter, Depends
from .. import models
from ..deps import get_current_user
from ..services import fx_rates

router = APIRouter(prefix="/fx", tags=["fx"])


@router.get("/rates")
def rates(current_user: models.User = Depends(get_current_user)):
    """Rates for every supported currency relative to 1 INR, refreshed
    from a live source roughly every 6 hours. Requires auth only to stay
    consistent with the rest of the API; the data itself isn't per-user."""
    return fx_rates.get_rates()
