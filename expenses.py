import csv
import datetime as dt
import io
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from ..i18n import tr
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user
from ..services.categorizer import categorize
from ..services import receipt_parser

router = APIRouter(prefix="/expenses", tags=["expenses"])


@router.post("", response_model=schemas.ExpenseOut, status_code=201)
def create_expense(
    payload: schemas.ExpenseCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    category = payload.category or categorize(payload.merchant, payload.note)
    exp = models.Expense(
        user_id=current_user.id,
        amount=payload.amount,
        category=category,
        merchant=payload.merchant,
        payment_method=payload.payment_method,
        note=payload.note,
        timestamp=payload.timestamp or dt.datetime.utcnow(),
        location=payload.location,
        device_usage=payload.device_usage,
        screen_time_minutes=payload.screen_time_minutes,
        source=payload.source,
    )
    db.add(exp)
    db.commit()
    db.refresh(exp)
    return exp


def _recent_for_duplicates(db: Session, user_id: int) -> list:
    since = dt.datetime.utcnow() - dt.timedelta(days=60)
    rows = db.query(models.Expense).filter(
        models.Expense.user_id == user_id, models.Expense.timestamp >= since).all()
    return [{"id": r.id, "amount": r.amount, "merchant": r.merchant or "", "timestamp": r.timestamp} for r in rows]


def _merchant_history(db: Session, user_id: int) -> list:
    rows = db.query(models.Expense.merchant, models.Expense.category).filter(
        models.Expense.user_id == user_id, models.Expense.merchant != "").order_by(
        models.Expense.timestamp.desc()).limit(500).all()
    return [{"merchant": m, "category": c} for m, c in rows]


@router.post("/parse-receipt")
def parse_receipt(
    payload: schemas.ReceiptParseRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Turn OCR text from a scanned/photographed bill into an expense draft.
    Nothing is saved here -- the client reviews the draft and then POSTs it."""
    texts = [payload.text] + [t[:20000] for t in payload.alt_texts]
    return receipt_parser.parse_receipt_texts(
        texts, _recent_for_duplicates(db, current_user.id), history=_merchant_history(db, current_user.id))


@router.post("/quick-parse")
def quick_parse(
    payload: schemas.TextParseRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Natural-language quick-add: "450 swiggy dinner upi yesterday"."""
    return receipt_parser.parse_quick_text(payload.text, _recent_for_duplicates(db, current_user.id))


_ALIASES = {
    "date": ("date", "timestamp", "time", "when", "day"),
    "amount": ("amount", "debit", "withdrawal", "value", "total", "price", "cost", "spent"),
    "merchant": ("merchant", "description", "payee", "name", "narration", "details", "vendor", "title"),
    "category": ("category", "type"),
    "payment_method": ("payment_method", "payment", "method", "mode", "account"),
    "note": ("note", "notes", "memo", "remarks", "comment"),
}
_DATE_FORMATS = ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y",
                 "%m/%d/%Y", "%d %b %Y", "%d %B %Y", "%b %d, %Y", "%d-%b-%Y", "%Y/%m/%d")
_CATS = {"food", "groceries", "shopping", "transport", "bills", "entertainment", "health", "others"}


def _parse_date(raw: str) -> Optional[dt.datetime]:
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        return dt.datetime.fromisoformat(raw.replace("Z", ""))
    except ValueError:
        pass
    for f in _DATE_FORMATS:
        try:
            return dt.datetime.strptime(raw, f)
        except ValueError:
            continue
    return None


def _parse_amount(raw: str) -> Optional[float]:
    import re
    txt = re.sub(r"[^\d.,\-]", "", raw or "")
    if not re.search(r"\d", txt):
        return None
    if "," in txt and "." in txt:
        txt = txt.replace(",", "")
    elif "," in txt:
        txt = txt.replace(",", "") if re.fullmatch(r"-?\d{1,3}(,\d{3})+", txt) else txt.replace(",", ".")
    try:
        v = abs(float(txt))
    except ValueError:
        return None
    return v if v > 0 else None


@router.post("/import-csv")
def import_csv(payload: schemas.CsvImport, db: Session = Depends(get_db),
               current_user: models.User = Depends(get_current_user)):
    """Bring in expenses from a bank/spreadsheet export. Needs a header row with at least date + amount."""
    reader = csv.reader(io.StringIO(payload.csv_text.lstrip("\ufeff")))
    rows = list(reader)
    if len(rows) < 2:
        raise HTTPException(status_code=422, detail=tr("The file has no data rows."))
    header = [h.strip().lower().replace(" ", "_") for h in rows[0]]
    col = {}
    for key, names in _ALIASES.items():
        for n in names:
            if n in header:
                col[key] = header.index(n)
                break
    if "date" not in col or "amount" not in col:
        raise HTTPException(status_code=422, detail=tr("Couldn't find a date and an amount column in the first row."))
    existing = {(e.timestamp.date(), round(e.amount, 2), (e.merchant or "").lower())
                for e in db.query(models.Expense).filter(models.Expense.user_id == current_user.id)}
    added = skipped = dupes = 0
    for r in rows[1:5001]:
        if not any(c.strip() for c in r):
            continue
        get = lambda k: (r[col[k]].strip() if k in col and col[k] < len(r) else "")
        ts, amt = _parse_date(get("date")), _parse_amount(get("amount"))
        if not ts or not amt:
            skipped += 1
            continue
        merchant = get("merchant")[:200]
        key = (ts.date(), round(amt, 2), merchant.lower())
        if key in existing:
            dupes += 1
            continue
        existing.add(key)
        cat = get("category").title() if get("category").lower() in _CATS else categorize(merchant, get("note"))
        db.add(models.Expense(user_id=current_user.id, amount=amt, category=cat, merchant=merchant,
                              payment_method=get("payment_method")[:40] or "Other", note=get("note")[:500],
                              timestamp=ts, location="", device_usage="", screen_time_minutes=0, source="csv"))
        added += 1
    db.commit()
    return {"added": added, "skipped": skipped, "duplicates": dupes}


@router.get("/export.csv")
def export_csv(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Download all of the user's expenses as a spreadsheet-friendly CSV."""
    rows = db.query(models.Expense).filter(models.Expense.user_id == current_user.id) \
        .order_by(models.Expense.timestamp.desc()).all()
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["date", "time", "amount", "category", "merchant", "payment_method", "note", "source"])

    def safe(v):  # block spreadsheet formula injection from user-typed text
        v = "" if v is None else str(v)
        return "'" + v if v[:1] in ("=", "+", "-", "@") else v
    for e in rows:
        w.writerow([e.timestamp.strftime("%Y-%m-%d"), e.timestamp.strftime("%H:%M"), e.amount, e.category,
                    safe(e.merchant), e.payment_method, safe(e.note), e.source or "manual"])
    return StreamingResponse(
        iter([buf.getvalue()]), media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=spendsense-expenses.csv"})


@router.get("", response_model=List[schemas.ExpenseOut])
def list_expenses(
    category: Optional[str] = None,
    q: Optional[str] = None,
    start: Optional[dt.date] = None,
    end: Optional[dt.date] = None,
    limit: int = 500,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    query = db.query(models.Expense).filter(models.Expense.user_id == current_user.id)
    if category:
        query = query.filter(models.Expense.category == category)
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(
            models.Expense.merchant.ilike(like) | models.Expense.note.ilike(like) | models.Expense.category.ilike(like))
    if start:
        query = query.filter(models.Expense.timestamp >= dt.datetime.combine(start, dt.time.min))
    if end:
        query = query.filter(models.Expense.timestamp <= dt.datetime.combine(end, dt.time.max))
    return query.order_by(models.Expense.timestamp.desc()).limit(min(max(limit, 1), 2000)).all()


@router.patch("/{expense_id}", response_model=schemas.ExpenseOut)
def update_expense(
    expense_id: int,
    payload: schemas.ExpenseUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    exp = db.query(models.Expense).filter(
        models.Expense.id == expense_id, models.Expense.user_id == current_user.id
    ).first()
    if not exp:
        raise HTTPException(status_code=404, detail=tr("Expense not found"))
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        if v is not None:
            setattr(exp, k, v)
    # changed merchant/note but not the category -> re-run auto-categorisation
    if ("merchant" in data or "note" in data) and "category" not in data:
        exp.category = categorize(exp.merchant, exp.note)
    db.commit()
    db.refresh(exp)
    return exp


@router.delete("/{expense_id}", status_code=204)
def delete_expense(
    expense_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    exp = db.query(models.Expense).filter(
        models.Expense.id == expense_id, models.Expense.user_id == current_user.id
    ).first()
    if not exp:
        raise HTTPException(status_code=404, detail=tr("Expense not found"))
    db.delete(exp)
    db.commit()
    return None
