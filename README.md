# UM Tech ServiceLayer
### Customer Retention & Churn Risk API

A production-grade REST API built with **FastAPI + PostgreSQL** that powers the full customer retention pipeline:

```
Transaction → Review → Data → Campaign → Retention
```

---

## Architecture

```
um-tech-servicelayer/
├── app/
│   ├── main.py                 # FastAPI app, routers, CORS
│   ├── database.py             # SQLAlchemy engine + session
│   ├── models/
│   │   └── models.py           # ORM tables: customers, transactions, feedback, churn_scores, campaigns
│   ├── schemas/
│   │   └── schemas.py          # Pydantic request/response schemas
│   ├── routers/
│   │   ├── auth.py             # POST /auth/register, /login, /me
│   │   ├── customers.py        # CRUD + /customers/at-risk
│   │   ├── transactions.py     # CRUD transactions
│   │   ├── feedback.py         # CRUD feedback
│   │   ├── churn.py            # Churn scores + recalculation
│   │   └── campaigns.py        # Campaign management
│   └── services/
│       ├── auth_service.py     # JWT + bcrypt
│       └── churn_service.py    # ⚡ Core churn business logic
├── tests/
│   └── test_api.py             # Full pytest test suite
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env.example
```

---

## Database Schema

```
customers          transactions         feedback
──────────         ────────────         ────────
id                 id                   id
email              customer_id ──┐      customer_id ──┐
full_name          amount        │      score (1-5)   │
phone              currency      │      category      │
segment            product_name  │      comment       │
is_active          status        │      created_at    │
created_at         transaction_ref      created_at    │
                   created_at    │                    │
                                 │                    │
churn_scores       campaigns     │      campaign_customers
────────────       ─────────     │      ───────────────────
id                 id            │      campaign_id
customer_id ◄──┐  name          │      customer_id ◄─┘
risk_level     │  description   │      sent_at
score          └──target_risk   │      opened_at
days_since_purchase  status     │      converted
avg_feedback_score   created_by └──────(via churn)
total_transactions
reasoning
calculated_at
```

---

## Churn Risk Business Logic

```python
# In app/services/churn_service.py

if days_since_last_purchase >= 60 AND avg_feedback_score < 3:
    risk = HIGH     # Companies pay for this signal

elif days_since_last_purchase >= 30 OR avg_feedback_score < 3:
    risk = MEDIUM

else:
    risk = LOW

# Composite score (0.0 – 1.0) for ranking:
score = (recency_weight * 0.6) + (feedback_weight * 0.35) + volume_bonus
```

Churn scores **auto-update** every time a new transaction or feedback is submitted.

---

## Quick Start

### 1. Clone & configure

```bash
cp .env.example .env
# Edit .env with your values
```

### 2. Run with Docker (recommended)

```bash
docker-compose up --build
```

API available at `http://localhost:8000`
Interactive docs at `http://localhost:8000/docs`

### 3. Run locally (manual)

```bash
# Install dependencies
pip install -r requirements.txt

# Start PostgreSQL (or use Docker just for DB)
docker run -d -e POSTGRES_USER=umtech -e POSTGRES_PASSWORD=umtech_pass \
  -e POSTGRES_DB=umtech_db -p 5432:5432 postgres:16

# Start API
uvicorn app.main:app --reload
```

### 4. Run tests (uses SQLite, no PostgreSQL needed)

```bash
pytest tests/ -v
```

---

## API Reference

All endpoints except `/`, `/health`, `/auth/register`, and `/auth/login` require a Bearer token.

### Authentication

#### Register
```http
POST /auth/register
Content-Type: application/json

{
  "email": "admin@company.com",
  "password": "securepass123",
  "full_name": "Jane Admin",
  "role": "admin"
}
```

#### Login
```http
POST /auth/login
Content-Type: application/json

{
  "email": "admin@company.com",
  "password": "securepass123"
}
```
**Response:**
```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer",
  "user": { "id": 1, "email": "admin@company.com", "role": "admin" }
}
```

---

### Customers

#### Create customer
```http
POST /customers
Authorization: Bearer <token>

{
  "email": "alice@example.com",
  "full_name": "Alice Johnson",
  "phone": "+27-21-555-0101",
  "segment": "vip"
}
```

#### List customers (paginated)
```http
GET /customers?skip=0&limit=20&segment=vip
Authorization: Bearer <token>
```

#### Get one customer
```http
GET /customers/42
Authorization: Bearer <token>
```

#### Update customer
```http
PUT /customers/42
Authorization: Bearer <token>

{ "segment": "at-risk" }
```

#### Soft-delete customer
```http
DELETE /customers/42
Authorization: Bearer <token>
```

#### ⚠️ Get at-risk customers (HIGH + MEDIUM churn)
```http
GET /customers/at-risk
Authorization: Bearer <token>
```
```json
[
  {
    "id": 7,
    "email": "bob@example.com",
    "full_name": "Bob Chen",
    "segment": "standard",
    "churn_risk": "HIGH",
    "churn_score": 0.847
  }
]
```

Filter by specific risk level:
```http
GET /customers/at-risk?risk_level=HIGH
```

---

### Transactions

#### Record a purchase
```http
POST /transactions
Authorization: Bearer <token>

{
  "customer_id": 42,
  "amount": 299.00,
  "currency": "USD",
  "product_name": "Enterprise Plan",
  "status": "completed"
}
```
> Automatically recalculates the customer's churn score.

#### List transactions for a customer
```http
GET /transactions?customer_id=42&limit=50
Authorization: Bearer <token>
```

---

### Feedback

#### Submit feedback (score 1–5)
```http
POST /feedback
Authorization: Bearer <token>

{
  "customer_id": 42,
  "score": 2,
  "category": "support",
  "comment": "Response time was too slow"
}
```
> Score < 3 triggers medium/high churn risk flag. Automatically recalculates churn.

#### Filter feedback by score
```http
GET /feedback?customer_id=42&max_score=2
Authorization: Bearer <token>
```

---

### Churn Scores

#### Get churn score for a customer
```http
GET /churn/42
Authorization: Bearer <token>
```
```json
{
  "customer_id": 42,
  "risk_level": "HIGH",
  "score": 0.783,
  "days_since_purchase": 67,
  "avg_feedback_score": 2.1,
  "total_transactions": 3,
  "reasoning": "No purchase for 67 days (≥60 threshold); Avg feedback 2.1 is below 3.0",
  "calculated_at": "2026-03-10T09:00:00"
}
```

#### List all churn scores (sorted by risk)
```http
GET /churn?risk_level=HIGH&limit=100
Authorization: Bearer <token>
```

#### Force recalculate one customer
```http
POST /churn/42/recalculate
Authorization: Bearer <token>
```

#### Recalculate all customers (admin only)
```http
POST /churn/recalculate-all
Authorization: Bearer <token>
```

---

### Campaigns

#### Create a retention campaign
```http
POST /campaigns
Authorization: Bearer <token>

{
  "name": "Win-Back: HIGH Risk Q2",
  "description": "30% discount offer for customers at high churn risk",
  "target_risk": "HIGH",
  "status": "DRAFT"
}
```

#### Auto-target customers by risk level
```http
POST /campaigns/1/auto-target
Authorization: Bearer <token>
```
> Finds all customers with matching churn risk and adds them to the campaign.

#### Manually add customers
```http
POST /campaigns/1/add-customers
Authorization: Bearer <token>

{ "customer_ids": [7, 12, 45] }
```

#### Activate campaign
```http
PUT /campaigns/1
Authorization: Bearer <token>

{ "status": "ACTIVE" }
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql://umtech:umtech_pass@localhost:5432/umtech_db` | PostgreSQL connection string |
| `SECRET_KEY` | (insecure default) | JWT signing key — **change in production** |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | JWT expiry duration |

---

## Typical Retention Workflow

```
1. Customer data flows in via POST /transactions
2. Customer submits feedback via POST /feedback
3. Churn scores auto-recalculate after each event
4. Analyst queries GET /customers/at-risk to find who needs attention
5. Marketing creates POST /campaigns with target_risk=HIGH
6. POST /campaigns/{id}/auto-target fills the campaign automatically
7. Campaign is activated: PUT /campaigns/{id} { "status": "ACTIVE" }
8. Conversion tracked via campaign_customers.converted field
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | FastAPI 0.111 |
| Database | PostgreSQL 16 |
| ORM | SQLAlchemy 2.0 |
| Auth | JWT (python-jose) + bcrypt (passlib) |
| Validation | Pydantic v2 |
| Testing | pytest + httpx TestClient + SQLite |
| Container | Docker + Docker Compose |
