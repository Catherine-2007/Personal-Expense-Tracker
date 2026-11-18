"""
Database health check & self-repair. Run from anywhere (venv activated):
    python check_db.py            # report
    python check_db.py --repair   # also add missing columns / create tables
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.database import (Base, DATABASE_URL, database_status, engine,  # noqa: E402
                          run_lightweight_migrations)
from sqlalchemy import text  # noqa: E402
import app.models  # noqa: E402,F401

shown = DATABASE_URL.replace(engine.url.password, "***") if engine.url.password else DATABASE_URL
print(f"DATABASE_URL: {shown}")
print(f"Dialect:      {engine.dialect.name}")

try:
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    print("\n✅ Connected successfully.")
except Exception as e:  # noqa: BLE001
    print(f"\n❌ Connection FAILED: {e}")
    print("\nIf you're using XAMPP/MySQL, check:")
    print("  1. MySQL is started in the XAMPP Control Panel")
    print("  2. The database exists (python setup_mysql.py --db <name> creates it)")
    print("  3. backend/.env has: DATABASE_URL=mysql+pymysql://root:@127.0.0.1:3306/<name>")
    print("  4. You ran 'pip install -r requirements.txt'")
    sys.exit(1)

if "--repair" in sys.argv:
    Base.metadata.create_all(bind=engine)
    done = run_lightweight_migrations()
    print(f"🔧 Repair: {'added ' + ', '.join(done) if done else 'nothing to fix'}")

st = database_status()
print("\nTables (row counts):")
for name, n in st["tables"].items():
    print(f"  {name:<22}{n}")
missing_tables = set(Base.metadata.tables) - set(st["tables"])
if missing_tables:
    print(f"\n⚠️  Missing tables: {', '.join(sorted(missing_tables))}  -> run with --repair")
if st["missing_columns"]:
    print(f"\n⚠️  Missing columns: {st['missing_columns']}  -> run with --repair")
if st["ok"]:
    print("\n✅ Schema is up to date.")
else:
    print("\n❌ Schema needs attention (see above).")
    sys.exit(2)
