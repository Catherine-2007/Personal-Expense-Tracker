"""
Backend internationalisation.

Same idea as the frontend: the English sentence is the key.

    tr("You spent {amount} today", amount="₹450")

The active language is picked per request from the `Accept-Language` header
(the web app sends its own language id, e.g. "hi"), stored in a context
variable so service functions never need a `lang` parameter.

Catalogs live in app/locales/<lang>.json ({ "English": "Translation" }).
Missing keys fall back to English, so nothing is ever blank.

Some sentences are generated once and *stored* in the database in English
(trigger descriptions, intervention texts). `tr_stored()` translates those at
read time by matching them against the registered templates.
"""
import json
import re
from contextvars import ContextVar
from functools import lru_cache
from pathlib import Path

LANGS = ["en", "hi", "ta", "te", "bn", "mr", "gu", "kn", "ml", "pa", "es", "fr", "zz"]  # zz = pseudo-locale for tests
_LOCALES = Path(__file__).parent / "locales"
current_lang: ContextVar[str] = ContextVar("current_lang", default="en")

_templates: list[str] = []


def N_(text: str) -> str:
    """Mark a string for extraction without translating it yet."""
    return text


MONTHS = [N_(m) for m in (
    "January", "February", "March", "April", "May", "June", "July",
    "August", "September", "October", "November", "December")]


def month_year(d) -> str:
    """date -> 'October 2026' with the month name translated."""
    return f"{tr(MONTHS[d.month - 1])} {d.year}"


def parse_lang(header: str | None) -> str:
    """'hi-IN,hi;q=0.9,en;q=0.8' -> 'hi' (first supported language, else 'en')."""
    for part in (header or "").split(","):
        code = part.split(";")[0].strip().lower().split("-")[0]
        if code in LANGS:
            return code
    return "en"


@lru_cache(maxsize=32)
def _catalog(lang: str) -> dict:
    f = _LOCALES / f"{lang}.json"
    if lang == "en" or not f.exists():
        return {}
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _fill(text: str, vars: dict) -> str:
    if not vars:
        return text
    return re.sub(r"\{(\w+)\}", lambda m: str(vars[m.group(1)]) if m.group(1) in vars and vars[m.group(1)] is not None else m.group(0), text)


def tr(text: str, **vars) -> str:
    return _fill(_catalog(current_lang.get()).get(text, text), vars)


def tr_plural(n: int, one: str, other: str, **vars) -> str:
    return tr(one if n == 1 else other, n=n, **vars)


def register_template(text: str) -> str:
    """Declare a sentence that may be stored in the DB (English) and must be
    translated back later by tr_stored(). Returns the text (use like N_)."""
    if text not in _templates:
        _templates.append(text)
        _compiled.cache_clear()
    return text


@lru_cache(maxsize=1)
def _compiled():
    out = []
    for tpl in _templates:
        names = re.findall(r"\{(\w+)\}", tpl)
        pat = "^" + re.sub(r"\\\{(\w+)\\\}", lambda m: f"(?P<{m.group(1)}>.+?)", re.escape(tpl)) + "$"
        out.append((tpl, names, re.compile(pat, re.S)))
    return out


# words that appear inside stored sentences and should be translated too
_WORDS = ["Late Night", "Morning", "Afternoon", "Evening", "Weekend", "Weekday",
          "Food", "Groceries", "Shopping", "Transport", "Bills", "Entertainment", "Health", "Others", "Other"]


def tr_word(w: str) -> str:
    return tr(w.strip())


def tr_stored(text: str | None) -> str | None:
    """Translate a sentence that was stored in English, if we know its template."""
    if not text or current_lang.get() == "en":
        return text
    for tpl, names, rx in _compiled():
        m = rx.match(text)
        if m:
            vals = {k: _localize_value(v) for k, v in m.groupdict().items()}
            return tr(tpl, **vals)
    return tr(text)


def _localize_value(v: str) -> str:
    # "late night, weekend" -> translate each known word, keep unknown parts
    def word(mm):
        return tr(mm.group(0).title() if mm.group(0).lower() in {w.lower() for w in _WORDS} else mm.group(0))
    parts = re.split(r"(\s*[,+]\s*)", v)
    out = []
    for p in parts:
        key = next((w for w in _WORDS if w.lower() == p.strip().lower()), None)
        out.append(tr(key) if key else p)
    return "".join(out)
