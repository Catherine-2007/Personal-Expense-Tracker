"""Test setup: every test run uses a throw-away SQLite file, never your real database."""
import os
import tempfile

_tmp = tempfile.mkdtemp(prefix="spendsense-test-")
# Default: throw-away SQLite. To run the same suite against MySQL/MariaDB use an
# EMPTY scratch database:  TEST_DATABASE_URL=mysql+pymysql://root:@127.0.0.1/spendsense_test pytest
os.environ["DATABASE_URL"] = os.getenv("TEST_DATABASE_URL") or f"sqlite:///{_tmp}/test.db"
os.environ["RATE_LIMIT"] = "100000"
os.environ["AUTH_RATE_LIMIT"] = "100000"
