import os
import tempfile

# Configure an isolated SQLite DB *before* the app is imported.
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ["SEED_DEMO_DATA"] = "true"
os.environ["ENABLE_REMINDER_SCHEDULER"] = "false"
os.environ["OPENAI_API_KEY"] = ""
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-pytest-only-0123456789"
os.environ["AI_RATE_LIMIT_PER_MINUTE"] = "100"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

PASSWORD = "Password@123"


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


def login(client, email, password=PASSWORD) -> dict:
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="session")
def customer(client):
    return login(client, "customer@campusbite.dev")


@pytest.fixture(scope="session")
def customer2(client):
    return login(client, "customer2@campusbite.dev")


@pytest.fixture(scope="session")
def owner(client):
    return login(client, "owner@campusbite.dev")


@pytest.fixture(scope="session")
def owner2(client):
    return login(client, "owner2@campusbite.dev")


@pytest.fixture(scope="session")
def rider(client):
    return login(client, "rider@campusbite.dev")


@pytest.fixture(scope="session")
def rider2(client):
    return login(client, "rider2@campusbite.dev")
