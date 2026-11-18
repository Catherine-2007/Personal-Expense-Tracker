"""
Receipt & quick-text parser.

Turns *raw OCR text* (from a photographed/scanned bill) or a short typed /
spoken sentence ("450 swiggy dinner upi yesterday") into a structured
expense draft: merchant, total, date, payment method, category, line items,
tax, plus a per-field confidence so the UI can tell the user which fields to
double-check.

Design notes
------------
* Dependency-free (stdlib only) and deterministic -- easy to test and to
  reason about, in keeping with the rest of the app's "explainable, no black
  box" approach. OCR itself runs in the browser (tesseract.js), so the image
  never leaves the user's device; only the extracted text reaches this module.
* OCR text is noisy, so every step is defensive: O/0 and l/1 confusions in
  numbers, "12,50" vs "1,250" comma ambiguity, stray symbols, etc.
* Nothing is ever auto-saved. The caller always shows the draft for review.
"""
from __future__ import annotations

import datetime as dt
import difflib
import re
from typing import Dict, List, Optional, Tuple

from .categorizer import CATEGORY_KEYWORDS, categorize

# ----------------------------------------------------------------- numbers --

_CURRENCY_HINTS = [
    (re.compile(r"₹|\brs\.?\b|\binr\b", re.I), "INR"),
    (re.compile(r"\$|\busd\b", re.I), "USD"),
    (re.compile(r"€|\beur\b", re.I), "EUR"),
    (re.compile(r"£|\bgbp\b", re.I), "GBP"),
    (re.compile(r"\baed\b|\bdhs?\b", re.I), "AED"),
    (re.compile(r"¥|\bjpy\b", re.I), "JPY"),
]

# A money-looking token: optional currency marker, then digits with optional
# thousands separators and an optional 1-2 digit decimal part.
_MONEY_RE = re.compile(
    r"(?<![\w/:.-])(?:(?:rs\.?|inr|₹|\$|€|£)\s*)?"
    r"(\d{1,3}(?:,\d{2,3})+(?:\.\d{1,2})?|\d+(?:[.,]\d{1,2})?)(?![\w/:%-])",
    re.I,
)


def _fix_ocr_digits(token: str) -> str:
    """Repair the usual OCR confusions *inside* an otherwise numeric token."""
    return (
        token.replace("O", "0").replace("o", "0")
        .replace("l", "1").replace("I", "1")
        .replace("S", "5").replace("B", "8")
    )


def _to_float(raw: str) -> Optional[float]:
    s = raw.strip()
    if not s:
        return None
    # "1,250.50" / "12,34,567" -> thousands separators
    if "," in s and "." in s:
        s = s.replace(",", "")
    elif "," in s:
        head, _, tail = s.rpartition(",")
        # "12,50" (two digits after the last comma, one comma) => decimal comma
        if len(tail) in (1, 2) and "," not in head:
            s = f"{head}.{tail}"
        else:
            s = s.replace(",", "")
    try:
        v = float(s)
    except ValueError:
        return None
    return v if v >= 0 else None


def _money_values(line: str) -> List[float]:
    out = []
    for m in _MONEY_RE.finditer(line):
        v = _to_float(m.group(1))
        if v is not None:
            out.append(v)
    return out


def detect_currency(text: str) -> Optional[str]:
    for rx, code in _CURRENCY_HINTS:
        if rx.search(text):
            return code
    return None


# ------------------------------------------------------------------- dates --

_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}

_DATE_NUMERIC = re.compile(r"\b(\d{1,4})[/\-.](\d{1,2})[/\-.](\d{2,4})\b")
_DATE_DMY_TEXT = re.compile(
    r"\b(\d{1,2})(?:st|nd|rd|th)?[\s\-/,.]*(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*[\s\-/,.]*(\d{2,4})\b", re.I)
_DATE_MDY_TEXT = re.compile(
    r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*[\s\-/,.]*(\d{1,2})(?:st|nd|rd|th)?[\s,.\-/]+(\d{2,4})\b", re.I)
_TIME_RE = re.compile(r"\b(\d{1,2})[:.](\d{2})(?::\d{2})?\s*(am|pm)?\b", re.I)


def _year(y: int) -> int:
    return 2000 + y if y < 100 else y


def _valid(y: int, m: int, d: int) -> Optional[dt.date]:
    try:
        return dt.date(y, m, d)
    except ValueError:
        return None


_DATE_GOOD = re.compile(r"\b(date|dt|dated|invoice|bill|time|txn|transaction|order)\b", re.I)
_DATE_BAD = re.compile(r"\b(exp|expiry|expires|best\s*before|mfg|manufactur|valid|due|gstin|reg|licen[sc]e|fssai|cin)\b", re.I)

# digits OCR commonly swaps for each other (thermal print / blur / low-res)
_CONFUSE = {"0": "689", "6": "08", "8": "036", "9": "08", "1": "7", "7": "1", "5": "63", "3": "85", "2": "7"}


def _digit_variants(num: str):
    yield num
    for i, ch in enumerate(num):
        for alt in _CONFUSE.get(ch, ""):
            yield num[:i] + alt + num[i + 1:]


def _repair_fields(a: str, b: str, c: str, today: dt.date):
    """If the literal reading isn't a plausible recent date, try one-digit OCR
    repairs (year first: "2626" -> "2026"). Returns (a, b, c, repaired)."""
    def plausible(a_, b_, c_):
        y = _year(int(c_))
        for d_, m_ in ((int(a_), int(b_)), (int(b_), int(a_))):
            cand = _valid(y, m_, d_)
            if cand and today - dt.timedelta(days=366 * 2) <= cand <= today + dt.timedelta(days=1):
                return True
        return False
    if plausible(a, b, c):
        return a, b, c, False
    for field in (2, 0, 1):
        src = (a, b, c)[field]
        for v in _digit_variants(src):
            if v == src:
                continue
            trial = [a, b, c]
            trial[field] = v
            if plausible(*trial):
                return trial[0], trial[1], trial[2], True
    return a, b, c, False


_DATE_COMPACT = re.compile(r"\b(\d{2})(\d{2})(20\d{2})\b")


def _line_candidates(line: str, today: Optional[dt.date] = None) -> List[Tuple[dt.date, float]]:
    today = today or dt.date.today()
    out: List[Tuple[dt.date, float]] = []
    for m in _DATE_DMY_TEXT.finditer(line):
        d, mon, y = int(m.group(1)), _MONTHS[m.group(2).lower()[:3]], _year(int(m.group(3)))
        c = _valid(y, mon, d)
        if c:
            out.append((c, 0.9))
    for m in _DATE_MDY_TEXT.finditer(line):
        mon, d, y = _MONTHS[m.group(1).lower()[:3]], int(m.group(2)), _year(int(m.group(3)))
        c = _valid(y, mon, d)
        if c:
            out.append((c, 0.9))
    if _DATE_GOOD.search(line):                      # "Date 12092026" (slashes lost)
        for m in _DATE_COMPACT.finditer(line):
            c = _valid(int(m.group(3)), int(m.group(2)), int(m.group(1)))
            if c:
                out.append((c, 0.55))
    for m in _DATE_NUMERIC.finditer(line):
        penalty = 0.0
        if len(m.group(1)) != 4:
            ra, rb, rc, fixed = _repair_fields(m.group(1), m.group(2), m.group(3), today)
            if fixed:
                penalty = 0.2
            a, b, c3 = int(ra), int(rb), int(rc)
        else:
            a, b, c3 = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if len(m.group(1)) == 4:                       # yyyy-mm-dd
            c, conf = _valid(a, b, c3), 0.9
        else:
            y = _year(c3)
            if b > 12 and a <= 12:                     # clearly mm/dd/yy
                c, conf = _valid(y, a, b), 0.8
            elif a > 12:                               # clearly dd/mm/yy
                c, conf = _valid(y, b, a), 0.9
            else:                                      # ambiguous -> dd/mm
                c, conf = _valid(y, b, a), 0.65
        if c:
            out.append((c, round(conf - penalty, 2)))
    return out


def parse_date(text: str, today: Optional[dt.date] = None) -> Tuple[Optional[dt.datetime], float]:
    """Return (datetime, confidence). Picks the best-scored date: lines
    labelled "Date"/"Invoice" win, expiry/registration dates lose, future and
    implausibly old dates are discarded. Prefers dd/mm unless impossible."""
    today = today or dt.date.today()
    lines = text.replace("\r", "\n").split("\n")
    best = None  # (score, date, conf, line_idx)
    for idx, raw in enumerate(lines):
        ln = _clean_lines(raw)
        ln = ln[0] if ln else ""
        if not ln:
            continue
        for cand, conf in _line_candidates(ln, today):
            if cand > today + dt.timedelta(days=1) or cand < today - dt.timedelta(days=366 * 3):
                continue
            score = conf + (0.5 if _DATE_GOOD.search(ln) else 0) - (1.0 if _DATE_BAD.search(ln) else 0) - idx * 0.002
            if best is None or score > best[0]:
                best = (score, cand, conf, idx)
    if not best:
        return None, 0.0
    _, found, conf, line_idx = best
    hh, mm = 12, 0
    scopes = [lines[line_idx], lines[line_idx + 1] if line_idx + 1 < len(lines) else "", text]
    for scope in scopes:
        tm = _TIME_RE.search(" ".join(_repair_token(t) for t in scope.split(" ")))
        if tm:
            h, mi = int(tm.group(1)), int(tm.group(2))
            ap = (tm.group(3) or "").lower()
            if ap == "pm" and h < 12:
                h += 12
            if ap == "am" and h == 12:
                h = 0
            if 0 <= h < 24 and 0 <= mi < 60:
                hh, mm = h, mi
                break
    return dt.datetime.combine(found, dt.time(hh, mm)), conf


# ------------------------------------------------------------- the receipt --

_SKIP_MERCHANT = re.compile(
    r"^(tax\s*invoice|invoice|bill|cash\s*memo|receipt|retail|original|duplicate|copy|"
    r"customer\s*copy|welcome|thank|gstin|gst\b|cin\b|fssai|tin\b|pan\b|ph\b|phone|tel\b|"
    r"mob|email|www\.|http|date|time|table|order|bill\s*no|inv\b|token|cashier|server)", re.I)

_TOTAL_PRIORITY = [
    (re.compile(r"grand\s*total|total\s*amount|amount\s*payable|net\s*payable|net\s*amount|"
                r"amount\s*due|balance\s*due|total\s*payable|bill\s*amount|total\s*due|"
                r"total\s*to\s*pay|amount\s*paid|you\s*pay", re.I), 0.95),
    (re.compile(r"\btotal\b", re.I), 0.85),
    (re.compile(r"\bpayable\b|\bamount\b|\bnet\b", re.I), 0.6),
]
_NOT_TOTAL = re.compile(
    r"sub\s*-?\s*total|total\s*(?:items?|qty|quantity|saving|savings|discount|gst|tax|cgst|sgst|igst|vat)|"
    r"items?\s*total|tax|gst|cgst|sgst|igst|vat|discount|saving|change|tendered|round|"
    r"points|balance\s*points|mrp|you\s*saved|tip|cash\s*given|received", re.I)

_NOT_ITEM = re.compile(
    r"total|sub\s*-?\s*total|tax|gst|cgst|sgst|igst|vat|cess|round|change|cash|card|upi|visa|master|"
    r"discount|saving|tendered|balance|amount|payable|qty|quantity|invoice|bill\s*no|date|time|"
    r"phone|tel\b|mob|gstin|fssai|table|order|token|points|paid|payment|service\s*charge|"
    r"thank|visit|www|http|mrp|rate|price|description|particulars|item\b", re.I)

_TAX_LINE = re.compile(r"\b(cgst|sgst|igst|utgst|vat|gst|service\s*tax|cess)\b", re.I)

_PAY_RULES: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"\bupi\b|gpay|google\s*pay|phone\s*pe|phonepe|paytm\s*upi|bhim|\bvpa\b|@(?:ok|ybl|paytm|upi|axl|ibl)", re.I), "UPI"),
    (re.compile(r"\bvisa\b|master\s*card|mastercard|rupay|\bamex\b|debit\s*card|credit\s*card|\bcard\b|\bpos\b|x{2,}\s*\d{4}|\*{2,}\s*\d{4}|\bapproval\b", re.I), "Card"),
    (re.compile(r"net\s*banking|\bneft\b|\bimps\b|bank\s*transfer", re.I), "Bank"),
    (re.compile(r"\bwallet\b|amazon\s*pay|mobikwik|freecharge", re.I), "Wallet"),
    (re.compile(r"\bcash\b|tendered|cash\s*given|change\s*due|\bchange\b", re.I), "Cash"),
]


_LOOKALIKE = {"O": "0", "o": "0", "Q": "0", "D": "0", "l": "1", "I": "1", "|": "1", "i": "1",
              "S": "5", "s": "5", "B": "8", "Z": "2", "z": "2", "G": "6", "g": "9", "q": "9", "T": "7"}
_NUMERIC_CHARS = set("0123456789.,:/-%")


def _repair_token(tok: str) -> str:
    """Fix OCR letter/digit confusions inside a token that is *meant* to be a
    number or date ("2B0.00" -> "280.00", "l5" -> "15", "872.OO" -> "872.00").
    Words are left alone: a token is only rewritten when every character is a
    digit, number punctuation or a known look-alike letter, and it holds at
    least one real digit."""
    prefix = ""
    m = re.match(r"^(rs\.?|inr|[₹$€£])", tok, re.I)
    if m:
        prefix, tok = m.group(0), tok[m.end():]
    if not tok or not any(c.isdigit() for c in tok):
        return prefix + tok
    if sum(1 for c in tok if c in _LOOKALIKE) > max(2, len(tok) // 2):
        return prefix + tok
    if all(c in _NUMERIC_CHARS or c in _LOOKALIKE for c in tok):
        tok = "".join(_LOOKALIKE.get(c, c) for c in tok)
    return prefix + tok


def _clean_lines(text: str) -> List[str]:
    lines = []
    for raw in text.replace("\r", "\n").split("\n"):
        ln = re.sub(r"[|_~`]+", " ", raw)
        ln = re.sub(r"[ \t]+", " ", ln).strip()
        if not ln:
            continue
        # rejoin amounts the OCR split: "872 .00" / "872. 00"
        ln = re.sub(r"(\d)\s+([.,])\s*(\d{2})\b", r"\1\2\3", ln)
        ln = re.sub(r"(\d)\s*([.,])\s+(\d{2})\b", r"\1\2\3", ln)
        ln = " ".join(_repair_token(t) for t in ln.split(" "))
        lines.append(ln)
    return lines


def _alpha_ratio(s: str) -> float:
    letters = sum(c.isalpha() for c in s)
    return letters / max(len(s.replace(" ", "")), 1)


def _known_brand(text: str) -> Optional[str]:
    low = text.lower()
    best = None
    for kws in CATEGORY_KEYWORDS.values():
        for kw in kws:
            # only brand-like keywords (single word, >=4 chars, not generic nouns)
            if len(kw) >= 4 and " " not in kw and re.search(rf"\b{re.escape(kw)}\b", low):
                if kw in _GENERIC_WORDS:
                    continue
                if best is None or low.find(kw) < low.find(best):
                    best = kw
    return best.title() if best else None


_GENERIC_WORDS = {
    "food", "store", "game", "party", "snack", "candy", "eat", "delivery", "bill",
    "shopping", "clothes", "shoes", "mall", "rent", "water", "doctor", "medicine",
    "dinner", "lunch", "breakfast", "movie", "cinema", "gym", "clinic", "taxi",
    "auto", "bus", "fuel", "petrol", "parking", "metro", "sweets", "vegetables",
    "grocery", "restaurant", "subscription", "insurance", "recharge", "broadband",
    "electronics", "concert", "hospital", "pharmacy", "chocolate", "emi",
}


def _guess_merchant(lines: List[str]) -> Tuple[str, float]:
    head = lines[:8]
    for ln in head:
        if _SKIP_MERCHANT.match(ln):
            continue
        if re.search(r"\d{5,}", ln):          # phone/GSTIN/long ids
            continue
        if _alpha_ratio(ln) < 0.6 or sum(c.isalpha() for c in ln) < 3:
            continue
        name = re.sub(r"[^A-Za-z0-9&'\-\. ]", "", ln).strip(" .-")
        # needs a real word: >=3 letters incl. a vowel (rejects OCR noise like "Ne J 3")
        if not any(len(w) >= 3 and re.search(r"[aeiouAEIOU]", w) and w.isalpha() for w in name.split()) \
                and not re.fullmatch(r"[A-Za-z]{2,5}\s*[A-Za-z]{2,6}", name):
            continue
        if len(name) >= 3:
            # Title-case SHOUTING receipts so they look natural
            return (name.title() if name.isupper() else name), 0.75
    brand = _known_brand(" ".join(lines))
    if brand:
        return brand, 0.6
    return "", 0.0


def _total_candidates(lines: List[str]) -> List[Tuple[float, float, int]]:
    """Every plausible 'the bill total is X' line: (value, confidence, line index)."""
    cands: List[Tuple[float, float, int]] = []
    for i, ln in enumerate(lines):
        if _NOT_TOTAL.search(ln):
            continue
        for rx, conf in _TOTAL_PRIORITY:
            if rx.search(ln):
                vals = _money_values(ln)
                if not vals and i + 1 < len(lines):      # amount wrapped to next line
                    vals = _money_values(lines[i + 1])[:1]
                if vals:
                    cands.append((vals[-1], conf, i))
                break
    return cands


def _find_subtotal(lines: List[str]) -> Optional[float]:
    for ln in lines:
        if re.search(r"sub\s*-?\s*total", ln, re.I):
            vals = _money_values(ln)
            if vals:
                return vals[-1]
    return None


def _find_total(lines: List[str]) -> Tuple[Optional[float], float]:
    cands = _total_candidates(lines)
    if cands:
        # higher confidence first; on a tie the LATER line (grand totals sit at the bottom)
        v, conf, _ = max(cands, key=lambda c: (c[1], c[2]))
        return v, conf
    pool = []                       # fallback: largest decimal-looking amount
    for ln in lines:
        if _NOT_TOTAL.search(ln) or re.search(r"\d{7,}", ln) or _DATE_NUMERIC.search(ln):
            continue
        pool.extend(v for v in _money_values(ln) if v > 0)
    if pool:
        return max(pool), 0.4
    return None, 0.0


_ADDRESS = re.compile(r"\b(ph|road|rd|street|st|nagar|floor|sector|plot|opp|near|pin|pincode|"
                      r"lane|colony|market|bazaar|city|district|state)\b|\b\d{5,}\b", re.I)


def _find_items(lines: List[str]) -> List[Dict]:
    items: List[Dict] = []
    for ln in lines:
        if _NOT_ITEM.search(ln) or _DATE_NUMERIC.search(ln) or _ADDRESS.search(ln):
            continue
        vals = _money_values(ln)
        if not vals:
            continue
        amount = vals[-1]
        # item name = text before the first digit run that begins the numeric tail
        name = re.split(r"\s+\d+(?:[.,]\d+)?\s*(?:x|@|\*)?\s*\d|\s+\d+(?:[.,]\d{1,2})?\s*$", ln, maxsplit=1)[0]
        name = re.sub(r"[^A-Za-z0-9&'\-\. /()]", " ", name)
        name = re.sub(r"\s+", " ", name).strip(" .-x*")
        if len(name) < 2 or _alpha_ratio(name) < 0.5 or amount <= 0:
            continue
        items.append({"name": name.title() if name.isupper() else name, "amount": round(amount, 2)})
        if len(items) >= 25:
            break
    return items


def _find_tax(lines: List[str]) -> Optional[float]:
    total_tax = 0.0
    seen = False
    for ln in lines:
        if "gstin" in ln.lower() or re.search(r"total\s*(items|qty)", ln, re.I):
            continue
        if _TAX_LINE.search(ln):
            vals = _money_values(ln)
            # drop the percentage ("CGST 9%") if it parsed as a value
            vals = [v for v in vals if not re.search(rf"{re.escape(str(int(v)))}\s*%", ln)] or vals
            if vals:
                total_tax += vals[-1]
                seen = True
    return round(total_tax, 2) if seen else None


def _find_payment(text: str) -> Tuple[Optional[str], float]:
    for rx, label in _PAY_RULES:
        if rx.search(text):
            return label, 0.8
    return None, 0.0


def _norm_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (name or "").lower())


def _snap_to_history(name: str, history: List[dict]) -> Tuple[Optional[dict], float]:
    """Closest merchant the user has logged before (spelling-tolerant)."""
    n = _norm_name(name)
    if len(n) < 3 or not history:
        return None, 0.0
    best, best_r = None, 0.0
    for h in history:
        hn = _norm_name(h.get("merchant", ""))
        if len(hn) < 3:
            continue
        r = 1.0 if hn == n else difflib.SequenceMatcher(None, n, hn).ratio()
        if hn in n or n in hn:
            r = max(r, 0.9 if min(len(hn), len(n)) >= 5 else r)
        if r > best_r:
            best, best_r = h, r
    return (best, best_r) if best_r >= 0.8 else (None, best_r)


def _brand_words() -> List[str]:
    out = set()
    for kws in CATEGORY_KEYWORDS.values():
        for kw in kws:
            if len(kw) >= 5 and " " not in kw and kw not in _GENERIC_WORDS:
                out.add(kw)
    return sorted(out)


def _fuzzy_brand(lines: List[str]) -> Optional[str]:
    """A well-known brand hiding behind OCR typos ('Starbuoks' -> 'Starbucks')."""
    brands = _brand_words()
    for ln in lines[:8]:
        for tok in re.findall(r"[A-Za-z]{5,}", ln):
            m = difflib.get_close_matches(tok.lower(), brands, n=1, cutoff=0.84)
            if m:
                return m[0].title()
    return None


def _category_from_history(merchant: str, history: List[dict]) -> Optional[str]:
    n = _norm_name(merchant)
    if not n:
        return None
    counts: Dict[str, int] = {}
    for h in history:
        if _norm_name(h.get("merchant", "")) == n and h.get("category"):
            counts[h["category"]] = counts.get(h["category"], 0) + 1
    return max(counts, key=counts.get) if counts else None


def _match_existing(drafts_amount: Optional[float], merchant: str,
                    when: Optional[dt.datetime], existing: List[dict]) -> List[dict]:
    """Possible duplicates among the user's recent expenses."""
    if not drafts_amount:
        return []
    out = []
    for e in existing:
        if abs(e["amount"] - drafts_amount) > 0.01:
            continue
        if when and abs((e["timestamp"] - when).total_seconds()) > 36 * 3600:
            continue
        if merchant and e["merchant"]:
            sim = difflib.SequenceMatcher(None, merchant.lower(), e["merchant"].lower()).ratio()
            if sim < 0.55:
                continue
        out.append({"id": e["id"], "merchant": e["merchant"], "amount": e["amount"],
                    "timestamp": e["timestamp"].isoformat()})
    return out


def parse_receipt_text(text: str, existing: Optional[List[dict]] = None,
                       today: Optional[dt.date] = None,
                       history: Optional[List[dict]] = None) -> dict:
    """`existing` = recent expenses (duplicate detection); `history` =
    [{merchant, category}] from past expenses (spelling snap + category
    learning). Both optional."""
    history = history or []
    lines = _clean_lines(text or "")
    if not lines:
        return {"ok": False, "reason": "No readable text found in the image."}

    merchant, m_conf = _guess_merchant(lines)
    merchant_source = "header" if merchant else None
    snapped, _ratio = _snap_to_history(merchant, history)
    if snapped:                                       # "Apollo Pharmcy" -> "Apollo Pharmacy"
        merchant, m_conf, merchant_source = snapped["merchant"], max(m_conf, 0.92), "history"
    elif not merchant or m_conf < 0.7:
        fb = _fuzzy_brand(lines)
        if fb:
            merchant, m_conf, merchant_source = fb, max(m_conf, 0.7), "brand"
    if not snapped and merchant:
        fb = _fuzzy_brand([merchant])                 # typo'd header that is really a brand
        if fb and _norm_name(fb) not in _norm_name(merchant):
            merchant, m_conf, merchant_source = fb, max(m_conf, 0.75), "brand"

    cands = _total_candidates(lines)
    amount, a_conf = _find_total(lines)
    when, d_conf = parse_date(text, today)
    payment, p_conf = _find_payment(text)
    items = _find_items(lines)
    tax = _find_tax(lines)
    subtotal = _find_subtotal(lines)
    currency = detect_currency(text)

    # ---- arithmetic cross-checks: do the numbers on the bill agree? --------
    items_sum = round(sum(i["amount"] for i in items), 2)

    def tol(x):
        return max(1.0, 0.02 * x)

    def agrees(x: float) -> bool:
        if not x:
            return False
        refs = []
        if len(items) >= 2 and items_sum:
            refs += [items_sum, items_sum + (tax or 0)]
        if subtotal:
            refs += [subtotal, subtotal + (tax or 0)]
        return any(abs(r - x) <= tol(x) for r in refs)

    checks = {"items_match": None, "subtotal_tax_match": None}
    if amount is not None and cands and not agrees(amount):
        # the label-picked total disagrees with the arithmetic; another
        # total-looking line that DOES add up is more likely right (OCR dropped a digit)
        alt = [c for c in cands if agrees(c[0]) and c[1] >= a_conf - 0.2]
        if alt:
            amount, a_conf, _ = max(alt, key=lambda c: (c[1], c[2]))
    if amount is not None:
        if len(items) >= 2 and items_sum:
            checks["items_match"] = abs(items_sum - amount) <= tol(amount) or abs(items_sum + (tax or 0) - amount) <= tol(amount)
        if subtotal:
            checks["subtotal_tax_match"] = abs(subtotal + (tax or 0) - amount) <= tol(amount) or abs(subtotal - amount) <= tol(amount)

        def exact(ref):
            return abs(ref - amount) <= 0.011
        near_only = False
        if checks["items_match"] and items_sum and not (exact(items_sum) or exact(items_sum + (tax or 0))):
            near_only = True
        if subtotal and checks["subtotal_tax_match"] and not (exact(subtotal) or exact(subtotal + (tax or 0))):
            near_only = near_only or checks["items_match"] is not True
        if near_only and abs(items_sum - amount) < 0.5:
            a_conf = max(0.3, a_conf - 0.3)          # "close but not exact" usually means a misread digit
        elif checks["items_match"] or checks["subtotal_tax_match"]:
            a_conf = min(0.99, a_conf + 0.1)
        elif checks["items_match"] is False and checks["subtotal_tax_match"] is not True:
            a_conf = max(0.3, a_conf - 0.15)         # numbers don't add up: ask the user to check

    alternatives: List[float] = []                    # one-tap fixes for the UI
    for v, _c, _i in sorted(cands, key=lambda c: (-c[1], -c[2])):
        if v != amount and v not in alternatives:
            alternatives.append(v)
    for extra in (items_sum if items else None, round(subtotal + (tax or 0), 2) if subtotal else None):
        if extra and extra != amount and extra not in alternatives:
            alternatives.append(extra)
    alternatives = alternatives[:4]

    item_text = " ".join(i["name"] for i in items[:12])
    category, category_source = None, "keywords"
    learned = _category_from_history(merchant, history)
    if learned:
        category, category_source = learned, "history"
    else:
        category = categorize(merchant, item_text) if (merchant or item_text) else "Others"
        if category == "Others":
            category = categorize("", " ".join(lines[:40]))

    note = ""
    if items:
        names = [i["name"] for i in items[:4]]
        note = (", ".join(names) + (f" +{len(items) - 4} more" if len(items) > 4 else ""))[:200]

    when_out = when or None
    return {
        "ok": amount is not None,
        "reason": None if amount is not None else "Couldn't find a total amount — please type it in.",
        "merchant": merchant,
        "merchant_source": merchant_source,
        "amount": amount,
        "amount_alternatives": alternatives,
        "timestamp": when_out.isoformat() if when_out else None,
        "payment_method": payment,
        "category": category,
        "category_source": category_source,
        "note": note,
        "items": items,
        "subtotal": subtotal,
        "tax": tax,
        "checks": checks,
        "currency_hint": currency,
        "confidence": {
            "merchant": round(m_conf, 2), "amount": round(a_conf, 2),
            "date": round(d_conf, 2), "payment_method": round(p_conf, 2),
        },
        "possible_duplicates": _match_existing(amount, merchant, when_out, existing or []),
    }


def _quality(r: dict) -> float:
    """How trustworthy is one OCR pass's parse? Used to pick the best of several."""
    if not r.get("ok"):
        return -1.0
    c = r["confidence"]
    q = 2.0 * c["amount"] + c["merchant"] + c["date"] + 0.5 * c["payment_method"]
    if r["checks"].get("items_match") or r["checks"].get("subtotal_tax_match"):
        q += 1.0
    q += min(len(r["items"]), 6) * 0.05
    return q


def parse_receipt_texts(texts: List[str], existing: Optional[List[dict]] = None,
                        today: Optional[dt.date] = None,
                        history: Optional[List[dict]] = None) -> dict:
    """Parse several OCR passes of the SAME bill (differently pre-processed
    images) and keep the most self-consistent one. Independent agreement on the
    total raises confidence; disagreement lowers it so the UI asks for a check."""
    texts = [t for t in texts if t and t.strip()]
    if not texts:
        return {"ok": False, "reason": "No readable text found in the image."}
    results = [parse_receipt_text(t, existing, today, history) for t in texts]
    best = max(results, key=_quality)
    if best.get("ok"):
        agree = sum(1 for r in results if r.get("ok") and r["amount"] == best["amount"])
        if len(results) > 1:
            if agree >= 2:
                best["confidence"]["amount"] = round(min(0.99, best["confidence"]["amount"] + 0.08), 2)
            else:
                best["confidence"]["amount"] = round(max(0.3, best["confidence"]["amount"] - 0.1), 2)
        for r in results:
            if r.get("ok") and r["amount"] != best["amount"] and r["amount"] not in best["amount_alternatives"]:
                best["amount_alternatives"].append(r["amount"])
        best["amount_alternatives"] = best["amount_alternatives"][:4]
        # date vote: passes often differ by one misread digit. Majority wins.
        dated = [(r["timestamp"][:10], r["confidence"]["date"], r["timestamp"]) for r in results if r.get("timestamp")]
        if len(dated) > 1:
            tally: Dict[str, float] = {}
            ref = today or dt.date.today()
            for day, conf, _ts in dated:
                age = abs((ref - dt.date.fromisoformat(day)).days)
                recency = 0.35 if age <= 45 else 0.0          # receipts are usually fresh
                tally[day] = tally.get(day, 0) + conf + recency
            top = max(tally.items(), key=lambda kv: (kv[1], kv[0]))
            if best.get("timestamp", "")[:10] != top[0]:
                best["timestamp"] = next(ts for day, _c, ts in dated if day == top[0])
                best["confidence"]["date"] = round(min(best["confidence"]["date"], 0.65), 2)
            elif len({d for d, _c, _t in dated}) > 1:
                best["confidence"]["date"] = round(min(best["confidence"]["date"], 0.65), 2)
        for field in ("timestamp", "payment_method", "merchant"):   # fill gaps from other passes
            if not best.get(field):
                other = next((r[field] for r in results if r.get(field)), None)
                if other:
                    best[field] = other
                    key = "date" if field == "timestamp" else field
                    best["confidence"][key] = round(max(best["confidence"].get(key, 0), 0.55), 2)
    best["passes"] = len(results)
    return best


# ----------------------------------------------------- natural-language add --

_STOP = {
    "for", "at", "on", "in", "to", "from", "via", "using", "with", "by", "the", "a", "an",
    "paid", "pay", "spent", "spend", "bought", "buy", "purchase", "purchased", "ordered",
    "order", "got", "rs", "inr", "rupees", "rupee", "rupaye", "bucks", "of", "and", "my",
    "i", "was", "is", "cost", "costs", "worth", "amount", "ka", "ke", "ki",
}
_WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
_NUM_WORDS = re.compile(r"(?<![\w.])(?:rs\.?|inr|₹|\$|€|£)?\s*(\d+(?:[.,]\d+)?)\s*(k|thousand|lakh|lac)?\b(?!\s*(?:am|pm|:))", re.I)


def parse_quick_text(text: str, existing: Optional[List[dict]] = None,
                     today: Optional[dt.date] = None) -> dict:
    """'450 swiggy dinner upi yesterday' -> structured draft."""
    today = today or dt.date.today()
    raw = (text or "").strip()
    if not raw:
        return {"ok": False, "reason": "Say or type something like “450 swiggy dinner upi”."}

    work = raw.lower()

    # --- amount ---------------------------------------------------------
    amount: Optional[float] = None
    amt_span = None
    for m in _NUM_WORDS.finditer(work):
        val = _to_float(m.group(1))
        if val is None or val <= 0:
            continue
        mult = {"k": 1_000, "thousand": 1_000, "lakh": 100_000, "lac": 100_000}.get((m.group(2) or "").lower(), 1)
        amount, amt_span = round(val * mult, 2), m.span()
        break
    if amount is not None:
        work = work[:amt_span[0]] + " " + work[amt_span[1]:]

    # --- payment ---------------------------------------------------------
    payment, _ = _find_payment(work)
    for rx, label in _PAY_RULES:
        if label == payment:
            work = rx.sub(" ", work)
            break

    # --- date -------------------------------------------------------------
    when_date: Optional[dt.date] = None
    if re.search(r"\bday before yesterday\b", work):
        when_date = today - dt.timedelta(days=2)
        work = re.sub(r"\bday before yesterday\b", " ", work)
    elif re.search(r"\byesterday\b|\bkal\b", work):
        when_date = today - dt.timedelta(days=1)
        work = re.sub(r"\byesterday\b|\bkal\b", " ", work)
    elif re.search(r"\btoday\b|\baaj\b", work):
        when_date = today
        work = re.sub(r"\btoday\b|\baaj\b", " ", work)
    else:
        m = re.search(r"\b(\d{1,2})\s+days?\s+ago\b", work)
        if m:
            when_date = today - dt.timedelta(days=int(m.group(1)))
            work = work.replace(m.group(0), " ")
        else:
            m = re.search(r"\b(?:last\s+)?(" + "|".join(_WEEKDAYS) + r")\b", work)
            if m:
                target = _WEEKDAYS.index(m.group(1))
                delta = (today.weekday() - target) % 7 or 7
                when_date = today - dt.timedelta(days=delta)
                work = work.replace(m.group(0), " ")
    parsed_dt, _ = parse_date(raw, today)
    if parsed_dt and when_date is None:
        when_date = parsed_dt.date()
        work = _DATE_DMY_TEXT.sub(" ", _DATE_NUMERIC.sub(" ", work))
    when = dt.datetime.combine(when_date, dt.datetime.now().time().replace(microsecond=0)) if when_date else None
    if when and when.date() == today and when > dt.datetime.now():
        when = dt.datetime.now().replace(microsecond=0)

    # --- merchant / note -------------------------------------------------
    words = [w for w in re.findall(r"[a-z0-9&'\.\-]+", work) if w not in _STOP]
    brand = _known_brand(" ".join(words))
    merchant = brand or ""
    leftover = [w for w in words if not (brand and w == brand.lower())]
    if not merchant and leftover:
        merchant = leftover[0].title()
        leftover = leftover[1:]
    note = " ".join(leftover).strip()
    category = categorize(merchant, note) if (merchant or note) else "Others"

    ok = amount is not None
    return {
        "ok": ok,
        "reason": None if ok else "I couldn't find an amount — try “450 swiggy dinner upi”.",
        "merchant": merchant,
        "amount": amount,
        "timestamp": when.isoformat() if when else None,
        "payment_method": payment,
        "category": category,
        "note": note,
        "items": [],
        "tax": None,
        "currency_hint": detect_currency(raw),
        "confidence": {"merchant": 0.7 if merchant else 0.0, "amount": 0.95 if ok else 0.0,
                       "date": 0.9 if when else 0.0, "payment_method": 0.9 if payment else 0.0},
        "possible_duplicates": _match_existing(amount, merchant, when, existing or []),
    }
