import os
import time
from collections import defaultdict, deque
from dotenv import load_dotenv

load_dotenv()  # ensure .env is loaded before any module reads os.getenv(...)

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .database import Base, engine, run_lightweight_migrations, database_status
from . import bootstrap
from .i18n import current_lang, parse_lang, tr
from .routers import auth, expenses, goals, insights, interventions, reports, help_bot, motivation, fx, family, budgets

Base.metadata.create_all(bind=engine)
_applied = run_lightweight_migrations()
if _applied:
    print(f"[SpendSense] database upgraded, added: {', '.join(_applied)}")
if bootstrap.ensure_demo_data():
    print("[SpendSense] empty database detected -> seeded demo accounts (demo@spendsense.app / demo1234)")
if bootstrap.ensure_demo_family():
    print("[SpendSense] demo family created (invite code DEMO42)")
if bootstrap.rebase_demo_dates():
    print("[SpendSense] demo account timelines moved forward to today")

app = FastAPI(
    title="SpendSense-XAI API",
    description="Context-aware, explainable expense tracker with adaptive behavioral intervention.",
    version="1.0.0",
)

# --- CORS: restrict to the Vite dev server / configured origins only -----
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- minimal in-memory rate limiter (per IP, sliding window) -------------
# * CORS preflight (OPTIONS) requests are never counted -- every real call from
#   the browser produces one, which silently halved the budget before.
# * Normal API use: generous limit (a dashboard load fires ~20 requests).
# * Login / register: a much stricter limit to slow down password guessing.
RATE_LIMIT = int(os.getenv("RATE_LIMIT", "600"))     # requests per window, all endpoints
AUTH_RATE_LIMIT = int(os.getenv("AUTH_RATE_LIMIT", "30"))  # login/register attempts per window
RATE_WINDOW = 60                                      # seconds
_hits: dict[str, deque] = defaultdict(deque)
_auth_hits: dict[str, deque] = defaultdict(deque)


def _over_limit(bucket: deque, limit: int, now: float) -> bool:
    while bucket and now - bucket[0] > RATE_WINDOW:
        bucket.popleft()
    if len(bucket) >= limit:
        return True
    bucket.append(now)
    return False


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    # pick the response language for this request (see app/i18n.py)
    current_lang.set(parse_lang(request.headers.get("accept-language")))
    if request.method != "OPTIONS":
        ip = request.client.host if request.client else "unknown"
        now = time.time()
        is_auth = request.url.path in ("/auth/login", "/auth/register")
        if (is_auth and _over_limit(_auth_hits[ip], AUTH_RATE_LIMIT, now)) or _over_limit(_hits[ip], RATE_LIMIT, now):
            return JSONResponse(status_code=429, content={"detail": tr("Too many requests, slow down.")},
                                headers={"Access-Control-Allow-Origin": request.headers.get("origin", "*")})
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    return response


app.include_router(auth.router)
app.include_router(expenses.router)
app.include_router(goals.router)
app.include_router(insights.router)
app.include_router(interventions.router)
app.include_router(reports.router)
app.include_router(help_bot.router)
app.include_router(motivation.router)
app.include_router(fx.router)
app.include_router(family.router)
app.include_router(budgets.router)


@app.get("/")
def root():
    return {"status": "ok", "service": "SpendSense-XAI"}


@app.get("/health")
def health():
    st = database_status()
    # public endpoint: never expose table names / row counts of everyone's data
    return {"status": "healthy" if st["ok"] else "degraded", "database": {"dialect": st.get("dialect"), "ok": st["ok"], "fallback": st.get("fallback", False)}}
