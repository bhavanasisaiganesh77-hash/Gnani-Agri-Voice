import os
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["VOICE_STUDIO_DB"] = os.path.join(tempfile.mkdtemp(), "bootstrap.db")
for k in ("GNANI_API_KEY", "ANTHROPIC_API_KEY", "LLM_API_KEY", "LLM_PROVIDER"):
    os.environ.pop(k, None)

import pytest  # noqa: E402

import database as db  # noqa: E402
import ratelimit  # noqa: E402


@pytest.fixture
def fresh_db(tmp_path):
    db.DB_PATH = tmp_path / "test.db"
    db.init_db()
    ratelimit.reset()
    return db


@pytest.fixture
def user(fresh_db):
    u, err = fresh_db.create_user("farmer@example.com", "Ravi Kumar", "Passw0rd1", language="telugu")
    assert err is None, err
    return u
