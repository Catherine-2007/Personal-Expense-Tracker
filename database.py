"""
Database configuration.

Default: MySQL / MariaDB (XAMPP) -> database "spendsense-xai" on 127.0.0.1:3306,
user root, empty password. The database is created automatically if missing, so
everything you do in the app is stored there and visible in phpMyAdmin.

Override with DATABASE_URL in backend/.env:
    mysql+pymysql://root:@127.0.0.1:3306/spendsense-xai
    postgresql://user:password@localhost:5432/spendsense
    sqlite:///./spendsense.db          (file database, no server needed)

Which database is used (this was the "nothing is stored in MySQL" bug)
----------------------------------------------------------------------
* DATABASE_URL set (env var or backend/.env)  -> that database is used, and if it
  cannot be reached the app STOPS with a clear message. It never silently
  switches to another database.
* DATABASE_URL not set -> MySQL is tried first. Only if no MySQL server is
  running does the app fall back to SQLite, and it prints a loud banner and
  reports it in /health ("fallback": true) so you can never mistake it for MySQL.

Reliability notes
-----------------
* A relative SQLite path is anchored to the backend/ folder, NOT to the
  directory uvicorn was started from (previously, starting from another
  folder silently created a brand-new empty database).
* Schema upgrades run on every start for ALL databases: any column defined in
  models.py but missing in the database is added automatically.
* MySQL connections are pinged and recycled ("server has gone away" fix).
"""
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker, declarative_base

BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / ".env")
load_dotenv()


def _resolve_url(raw: str) -> str:
    url = make_url(raw)
    if url.drivername.startswith("sqlite") and url.database and url.database != ":memory:":
        db_path = Path(url.database)
        if not db_path.is_absolute():
            db_path = BACKEND_DIR / db_path
        url = url.set(database=str(db_path))
    return url.render_as_string(hide_password=False)


DEFAULT_MYSQL_URL = "mysql+pymysql://root:@127.0.0.1:3306/spendsense-xai?charset=utf8mb4"
SQLITE_FALLBACK_URL = "sqlite:///./spendsense.db"


def _ensure_mysql_database(raw: str) -> None:
    """CREATE DATABASE IF NOT EXISTS, so a missing database is never the reason nothing is saved."""
    url = make_url(raw)
    if not url.drivername.startswith("mysql") or not url.database:
        return
    server_url = url._replace(database=None)   # NB: URL.set(database=None) is a no-op
    tmp = create_engine(server_url, isolation_level="AUTOCOMMIT", pool_pre_ping=True)
    try:
        with tmp.connect() as conn:
            name = url.database.replace("`", "``")
            conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci"))
    finally:
        tmp.dispose()


def _make_engine(url: str):
    sqlite = url.startswith("sqlite")
    return create_engine(
        url,
        connect_args={"check_same_thread": False} if sqlite else {},
        pool_pre_ping=not sqlite,
        pool_recycle=280 if not sqlite else -1,
    )


def _select_engine():
    """Returns (url, engine, used_fallback). See the module docstring for the rules."""
    configured = os.getenv("DATABASE_URL", "").strip()
    if configured:
        url = _resolve_url(configured)
        try:
            _ensure_mysql_database(url)
            eng = _make_engine(url)
            with eng.connect() as conn:
                conn.execute(text("SELECT 1"))
        except Exception as e:  # noqa: BLE001
            shown = make_url(url).render_as_string(hide_password=True)
            raise RuntimeError(
                f"\n\n[SpendSense] Cannot connect to the database in DATABASE_URL:\n    {shown}\n"
                f"    {type(e).__name__}: {e}\n\n"
                "  - XAMPP: open the Control Panel and click Start next to MySQL\n"
                "  - Wrong password / port / name? Fix DATABASE_URL in backend/.env\n"
                "  - Want the file database instead? Set DATABASE_URL=sqlite:///./spendsense.db\n"
                "  (Data is NOT silently stored anywhere else.)\n") from e
        return url, eng, False

    try:
        _ensure_mysql_database(DEFAULT_MYSQL_URL)
        eng = _make_engine(DEFAULT_MYSQL_URL)
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        return DEFAULT_MYSQL_URL, eng, False
    except Exception as e:  # noqa: BLE001
        url = _resolve_url(SQLITE_FALLBACK_URL)
        bar = "!" * 70
        print(f"\n{bar}\n[SpendSense] WARNING: MySQL is not reachable ({type(e).__name__}).\n"
              f"  Falling back to the SQLite FILE: {make_url(url).database}\n"
              "  Nothing will appear in phpMyAdmin until MySQL is started.\n"
              "  -> XAMPP Control Panel: Start MySQL, then restart this server.\n"
              f"{bar}\n")
        return url, _make_engine(url), True


DATABASE_URL, engine, USING_FALLBACK = _select_engine()
_is_sqlite = DATABASE_URL.startswith("sqlite")
print(f"[SpendSense] database: {engine.dialect.name} -> "
      f"{make_url(DATABASE_URL).render_as_string(hide_password=True)}")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _column_ddl(column) -> str:
    type_sql = column.type.compile(dialect=engine.dialect)
    ddl = f"{engine.dialect.identifier_preparer.quote(column.name)} {type_sql}"
    default = column.default.arg if (column.default is not None and column.default.is_scalar) else None
    if default is not None:
        if isinstance(default, bool):
            ddl += f" DEFAULT {int(default)}"
        elif isinstance(default, (int, float)):
            ddl += f" DEFAULT {default}"
        else:
            safe = str(default).replace("'", "''")
            ddl += f" DEFAULT '{safe}'"
    return ddl


def missing_columns() -> dict:
    insp = inspect(engine)
    out = {}
    for table in Base.metadata.sorted_tables:
        if not insp.has_table(table.name):
            continue
        existing = {c["name"] for c in insp.get_columns(table.name)}
        gaps = [c.name for c in table.columns if c.name not in existing]
        if gaps:
            out[table.name] = gaps
    return out


def run_lightweight_migrations() -> list:
    """Adds newly-introduced columns to existing tables on any dialect.
    Returns the list of changes made (empty if already up to date)."""
    applied = []
    gaps = missing_columns()
    if not gaps:
        return applied
    with engine.begin() as conn:
        for table_name, cols in gaps.items():
            table = Base.metadata.tables[table_name]
            for col_name in cols:
                conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {_column_ddl(table.columns[col_name])}"))
                applied.append(f"{table_name}.{col_name}")
    return applied


def database_status() -> dict:
    info = {"dialect": engine.dialect.name, "ok": False, "tables": {}, "missing_columns": {},
            "fallback": USING_FALLBACK}
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            insp = inspect(engine)
            for table in Base.metadata.sorted_tables:
                if insp.has_table(table.name):
                    info["tables"][table.name] = conn.execute(text(f"SELECT COUNT(*) FROM {table.name}")).scalar()
        info["missing_columns"] = missing_columns()
        info["ok"] = not info["missing_columns"] and len(info["tables"]) == len(Base.metadata.tables)
    except Exception as e:  # noqa: BLE001
        info["error"] = str(e)
    if _is_sqlite:
        info["file"] = make_url(DATABASE_URL).database
    else:
        info["host"] = make_url(DATABASE_URL).host
    return info
