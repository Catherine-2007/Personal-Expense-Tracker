"""
Unusual-spend detector (robust statistics, explainable).

A purchase is compared with the user's OWN recent purchases in the same
category using the median and the median absolute deviation (MAD), which --
unlike mean/std -- isn't thrown off by one past big purchase. It is flagged
only when it is both >=2.5x the typical amount and a statistical outlier.
Needs >=5 comparable purchases; otherwise it stays quiet rather than guess.
"""
from __future__ import annotations

import datetime as dt
import statistics
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from .. import models
from ..i18n import tr

MIN_SAMPLES = 5


def _stats(amounts: List[float]) -> Optional[Dict]:
    if len(amounts) < MIN_SAMPLES:
        return None
    med = statistics.median(amounts)
    mad = statistics.median([abs(a - med) for a in amounts]) or max(med * 0.15, 1.0)
    return {"median": med, "mad": mad, "n": len(amounts)}


def check_amount(db: Session, user_id: int, category: str, amount: float,
                 exclude_id: Optional[int] = None) -> Dict:
    since = dt.datetime.utcnow() - dt.timedelta(days=120)
    q = db.query(models.Expense.amount).filter(
        models.Expense.user_id == user_id, models.Expense.category == category,
        models.Expense.timestamp >= since)
    if exclude_id:
        q = q.filter(models.Expense.id != exclude_id)
    st = _stats([a for (a,) in q.all()])
    if not st or amount <= 0:
        return {"unusual": False, "reason": tr("not enough history") if not st else tr("no amount")}
    ratio = amount / st["median"] if st["median"] else 0
    z = 0.6745 * (amount - st["median"]) / st["mad"]
    unusual = ratio >= 2.5 and z >= 3.5
    return {
        "unusual": unusual, "ratio": round(ratio, 1), "robust_z": round(z, 1),
        "typical": round(st["median"], 2), "samples": st["n"],
        "message": tr("That's about {ratio}× your usual {category} purchase (typically {typical}, based on {n} purchases).",
                      ratio=f"{ratio:.1f}", category=tr(category), typical=f"{st['median']:.0f}", n=st["n"]) if unusual else "",
    }


def recent_unusual(db: Session, user_id: int, days: int = 30, limit: int = 5) -> List[Dict]:
    since = dt.datetime.utcnow() - dt.timedelta(days=days)
    rows = db.query(models.Expense).filter(
        models.Expense.user_id == user_id, models.Expense.timestamp >= since
    ).order_by(models.Expense.timestamp.desc()).all()
    out = []
    for e in rows:
        res = check_amount(db, user_id, e.category, e.amount, exclude_id=e.id)
        if res["unusual"]:
            out.append({"id": e.id, "merchant": e.merchant, "category": e.category, "amount": e.amount,
                        "timestamp": e.timestamp.isoformat(), **res})
        if len(out) >= limit:
            break
    return out
