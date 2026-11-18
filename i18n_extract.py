"""Collect every translatable backend string -> app/locales/_keys.json
Run from backend/:  python scripts/i18n_extract.py"""
import ast, json, pathlib

APP = pathlib.Path(__file__).resolve().parent.parent / "app"
NAMES = {"tr", "N_", "register_template", "tr_word"}
keys = {}

def lit(n):
    if isinstance(n, ast.Constant) and isinstance(n.value, str):
        return n.value
    if isinstance(n, ast.JoinedStr):
        return None
    return None

for f in APP.rglob("*.py"):
    tree = ast.parse(f.read_text(encoding="utf-8"))
    for n in ast.walk(tree):
        if not isinstance(n, ast.Call):
            continue
        fn = n.func.id if isinstance(n.func, ast.Name) else getattr(n.func, "attr", "")
        if fn in NAMES and n.args:
            s = lit(n.args[0])
            if s: keys.setdefault(s, f"{f.name}:{n.lineno}")
        elif fn == "tr_plural" and len(n.args) >= 3:
            for a in n.args[1:3]:
                s = lit(a)
                if s: keys.setdefault(s, f"{f.name}:{n.lineno}")
    # words from the stored-sentence helper
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign) and any(getattr(t, "id", "") == "_WORDS" for t in n.targets):
            for e in n.value.elts:
                keys.setdefault(e.value, f"{f.name}:{n.lineno}")

for m in ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"):
    keys.setdefault(m, "i18n.py:MONTHS")

# help-bot keyword lists: translators supply "kw:<first keyword>" = "kw1|kw2|..." in their language
import sys
sys.path.insert(0, str(APP.parent))
from app.services.help_bot import FAQ_ENTRIES
kw_ref = {}
for e in FAQ_ENTRIES:
    k = "kw:" + e["keywords"][0]
    keys.setdefault(k, "help_bot.py")
    kw_ref[k] = "|".join(e["keywords"])
(APP / "locales").mkdir(exist_ok=True)
out = sorted(keys)
(APP / "locales" / "_keys.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
(APP / "locales" / "_kw_ref.json").write_text(json.dumps(kw_ref, ensure_ascii=False, indent=1), encoding="utf-8")
print(len(out), "backend strings -> app/locales/_keys.json")
