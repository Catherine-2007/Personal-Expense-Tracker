"""
One-command MySQL / MariaDB (XAMPP) setup.

    python setup_mysql.py                      # database "spendsense", user root, no password
    python setup_mysql.py --db spendsense-xai  # any database name (hyphens are fine)
    python setup_mysql.py --user root --password secret --host 127.0.0.1 --port 3306

What it does
  1. connects to your MySQL server (start MySQL in the XAMPP Control Panel first)
  2. creates the database if it does not exist (utf8mb4)
  3. writes DATABASE_URL into backend/.env so the app uses it
  4. creates every table and loads the demo accounts (demo@spendsense.app / demo1234)
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote_plus

HERE = Path(__file__).resolve().parent

ap = argparse.ArgumentParser()
ap.add_argument("--db", default="spendsense")
ap.add_argument("--user", default="root")
ap.add_argument("--password", default="")
ap.add_argument("--host", default="127.0.0.1")
ap.add_argument("--port", type=int, default=3306)
ap.add_argument("--no-demo", action="store_true", help="create empty tables, no demo accounts")
a = ap.parse_args()

try:
    import pymysql
except ImportError:
    sys.exit("PyMySQL is missing. Run:  pip install -r requirements.txt")

print(f"Connecting to MySQL at {a.host}:{a.port} as '{a.user}' ...")
try:
    conn = pymysql.connect(host=a.host, port=a.port, user=a.user, password=a.password)
except Exception as e:  # noqa: BLE001
    print(f"\n[X] Could not connect: {e}\n")
    print("  - Open the XAMPP Control Panel and click Start next to MySQL")
    print("  - XAMPP's default login is user 'root' with an empty password")
    print("  - If the port differs, pass --port 3307 (or whatever XAMPP shows)")
    sys.exit(1)

safe = a.db.replace("`", "``")
with conn.cursor() as cur:
    cur.execute(f"CREATE DATABASE IF NOT EXISTS `{safe}` CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci")
conn.commit()
conn.close()
print(f"[OK] Database `{a.db}` is ready")

url = f"mysql+pymysql://{quote_plus(a.user)}:{quote_plus(a.password)}@{a.host}:{a.port}/{quote_plus(a.db)}?charset=utf8mb4"
env = HERE / ".env"
if not env.exists():
    example = HERE / ".env.example"
    env.write_text(example.read_text() if example.exists() else "")
lines = [l for l in env.read_text().splitlines() if not re.match(r"\s*DATABASE_URL\s*=", l)]
lines.append(f"DATABASE_URL={url}")
env.write_text("\n".join(lines) + "\n")
print("[OK] backend/.env now points at MySQL")

code = (
    "import os;os.environ['AUTO_SEED']='0' if %r else '1';"
    "from app.database import Base, engine, run_lightweight_migrations;import app.models;"
    "Base.metadata.create_all(engine);run_lightweight_migrations();"
    "from app.bootstrap import ensure_demo_data;"
    "print('[OK] Tables created');"
    "print('[OK] Demo accounts loaded' if ensure_demo_data() else '[OK] No demo data added')"
) % a.no_demo
r = subprocess.run([sys.executable, "-c", code], cwd=HERE)
if r.returncode:
    sys.exit(r.returncode)
print("\nAll done. Start the app:  uvicorn app.main:app --reload")
print("Then open phpMyAdmin -> your database: you will see the tables and data.")
print("Login: demo@spendsense.app / demo1234")
