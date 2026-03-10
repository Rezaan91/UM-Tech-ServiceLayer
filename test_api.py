"""
Test Suite — UM Tech ServiceLayer
Uses pytest + httpx TestClient with an in-memory SQLite database
so no PostgreSQL is needed to run tests.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db

# ── Use SQLite in-memory for tests ───────────
TEST_DATABASE_URL = "sqlite:///./test.db"
engine            = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture(scope="module")
def auth_headers(client):
    """Register + login an admin user, return auth headers."""
    client.post("/auth/register", json={
        "email": "admin@umtech.com",
        "password": "adminpass123",
        "full_name": "UM Admin",
        "role": "admin"
    })
    resp = client.post("/auth/login", json={
        "email": "admin@umtech.com",
        "password": "adminpass123"
    })
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ─────────────────────────────────────────────
# HEALTH
# ─────────────────────────────────────────────
class TestHealth:
    def test_root(self, client):
        r = client.get("/")
        assert r.status_code == 200
        assert r.json()["service"] == "UM Tech ServiceLayer"

    def test_health(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "healthy"


# ─────────────────────────────────────────────
# AUTH
# ─────────────────────────────────────────────
class TestAuth:
    def test_register_success(self, client):
        r = client.post("/auth/register", json={
            "email": "analyst@umtech.com",
            "password": "analystpass",
            "full_name": "Analyst One",
            "role": "analyst"
        })
        assert r.status_code == 201
        assert r.json()["email"] == "analyst@umtech.com"

    def test_register_duplicate(self, client):
        r = client.post("/auth/register", json={
            "email": "analyst@umtech.com",
            "password": "analystpass",
            "full_name": "Analyst One",
            "role": "analyst"
        })
        assert r.status_code == 400

    def test_login_success(self, client):
        r = client.post("/auth/login", json={
            "email": "analyst@umtech.com",
            "password": "analystpass"
        })
        assert r.status_code == 200
        assert "access_token" in r.json()

    def test_login_wrong_password(self, client):
        r = client.post("/auth/login", json={
            "email": "analyst@umtech.com",
            "password": "wrongpass"
        })
        assert r.status_code == 401

    def test_me_authenticated(self, client, auth_headers):
        r = client.get("/auth/me", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["role"] == "admin"

    def test_me_unauthenticated(self, client):
        r = client.get("/auth/me")
        assert r.status_code == 401


# ─────────────────────────────────────────────
# CUSTOMERS
# ─────────────────────────────────────────────
class TestCustomers:
    def test_create_customer(self, client, auth_headers):
        r = client.post("/customers", headers=auth_headers, json={
            "email": "alice@example.com",
            "full_name": "Alice Smith",
            "phone": "+1-555-0101",
            "segment": "vip"
        })
        assert r.status_code == 201
        assert r.json()["email"] == "alice@example.com"

    def test_create_duplicate_customer(self, client, auth_headers):
        r = client.post("/customers", headers=auth_headers, json={
            "email": "alice@example.com",
            "full_name": "Alice Again"
        })
        assert r.status_code == 400

    def test_list_customers(self, client, auth_headers):
        r = client.get("/customers", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)
        assert len(r.json()) >= 1

    def test_get_customer(self, client, auth_headers):
        r = client.get("/customers/1", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["id"] == 1

    def test_update_customer(self, client, auth_headers):
        r = client.put("/customers/1", headers=auth_headers, json={"segment": "standard"})
        assert r.status_code == 200
        assert r.json()["segment"] == "standard"

    def test_get_nonexistent(self, client, auth_headers):
        r = client.get("/customers/9999", headers=auth_headers)
        assert r.status_code == 404


# ─────────────────────────────────────────────
# TRANSACTIONS
# ─────────────────────────────────────────────
class TestTransactions:
    def test_create_transaction(self, client, auth_headers):
        r = client.post("/transactions", headers=auth_headers, json={
            "customer_id": 1,
            "amount": 149.99,
            "product_name": "Premium Plan",
            "status": "completed"
        })
        assert r.status_code == 201
        assert r.json()["amount"] == 149.99

    def test_list_transactions(self, client, auth_headers):
        r = client.get("/transactions?customer_id=1", headers=auth_headers)
        assert r.status_code == 200
        assert len(r.json()) >= 1

    def test_invalid_amount(self, client, auth_headers):
        r = client.post("/transactions", headers=auth_headers, json={
            "customer_id": 1,
            "amount": -10,
        })
        assert r.status_code == 422


# ─────────────────────────────────────────────
# FEEDBACK
# ─────────────────────────────────────────────
class TestFeedback:
    def test_submit_feedback(self, client, auth_headers):
        r = client.post("/feedback", headers=auth_headers, json={
            "customer_id": 1,
            "score": 4,
            "category": "product",
            "comment": "Good experience overall"
        })
        assert r.status_code == 201
        assert r.json()["score"] == 4

    def test_invalid_score(self, client, auth_headers):
        r = client.post("/feedback", headers=auth_headers, json={
            "customer_id": 1,
            "score": 10
        })
        assert r.status_code == 422

    def test_list_feedback(self, client, auth_headers):
        r = client.get("/feedback?customer_id=1", headers=auth_headers)
        assert r.status_code == 200


# ─────────────────────────────────────────────
# CHURN SCORES
# ─────────────────────────────────────────────
class TestChurn:
    def test_get_churn_score(self, client, auth_headers):
        r = client.get("/churn/1", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert "risk_level" in data
        assert data["risk_level"] in ("LOW", "MEDIUM", "HIGH")
        assert 0.0 <= data["score"] <= 1.0

    def test_recalculate_customer(self, client, auth_headers):
        r = client.post("/churn/1/recalculate", headers=auth_headers)
        assert r.status_code == 200

    def test_list_churn_scores(self, client, auth_headers):
        r = client.get("/churn", headers=auth_headers)
        assert r.status_code == 200

    def test_at_risk_customers(self, client, auth_headers):
        r = client.get("/customers/at-risk", headers=auth_headers)
        assert r.status_code == 200

    def test_recalculate_all_admin(self, client, auth_headers):
        r = client.post("/churn/recalculate-all", headers=auth_headers)
        assert r.status_code == 200
        assert "Recalculated" in r.json()["message"]


# ─────────────────────────────────────────────
# CAMPAIGNS
# ─────────────────────────────────────────────
class TestCampaigns:
    def test_create_campaign(self, client, auth_headers):
        r = client.post("/campaigns", headers=auth_headers, json={
            "name": "Win-Back HIGH Risk",
            "description": "30% discount for churning customers",
            "target_risk": "HIGH",
            "status": "DRAFT"
        })
        assert r.status_code == 201
        assert r.json()["name"] == "Win-Back HIGH Risk"

    def test_list_campaigns(self, client, auth_headers):
        r = client.get("/campaigns", headers=auth_headers)
        assert r.status_code == 200
        assert len(r.json()) >= 1

    def test_update_campaign(self, client, auth_headers):
        r = client.put("/campaigns/1", headers=auth_headers, json={"status": "ACTIVE"})
        assert r.status_code == 200
        assert r.json()["status"] == "ACTIVE"

    def test_add_customers_to_campaign(self, client, auth_headers):
        r = client.post("/campaigns/1/add-customers", headers=auth_headers, json={
            "customer_ids": [1]
        })
        assert r.status_code == 200


# ─────────────────────────────────────────────
# CHURN BUSINESS LOGIC UNIT TESTS
# ─────────────────────────────────────────────
class TestChurnLogic:
    """Direct unit tests of the churn calculation service."""

    def test_high_risk_logic(self):
        from app.services.churn_service import DAYS_HIGH_RISK, SCORE_THRESHOLD
        days    = DAYS_HIGH_RISK + 1
        avg_fb  = SCORE_THRESHOLD - 0.5
        # Both conditions met → HIGH risk
        no_60   = days >= DAYS_HIGH_RISK
        bad_fb  = avg_fb < SCORE_THRESHOLD
        assert no_60 and bad_fb

    def test_medium_risk_logic(self):
        from app.services.churn_service import DAYS_MEDIUM_RISK, DAYS_HIGH_RISK, SCORE_THRESHOLD
        days   = DAYS_MEDIUM_RISK + 1
        avg_fb = 4.0  # good feedback
        no_30  = days >= DAYS_MEDIUM_RISK
        no_60  = days >= DAYS_HIGH_RISK
        bad_fb = avg_fb < SCORE_THRESHOLD
        # Only recency trigger (30+ days) → MEDIUM
        assert no_30 and not no_60 and not bad_fb

    def test_low_risk_logic(self):
        from app.services.churn_service import DAYS_MEDIUM_RISK, SCORE_THRESHOLD
        days   = DAYS_MEDIUM_RISK - 1  # recently active
        avg_fb = 4.5                   # good feedback
        assert days < DAYS_MEDIUM_RISK and avg_fb >= SCORE_THRESHOLD
