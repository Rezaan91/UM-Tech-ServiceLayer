"""
ORM Models — customers, transactions, feedback, churn_scores, campaigns
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean,
    DateTime, ForeignKey, Text, Enum
)
from sqlalchemy.orm import relationship
import enum

from app.database import Base


class ChurnRiskLevel(str, enum.Enum):
    LOW    = "LOW"
    MEDIUM = "MEDIUM"
    HIGH   = "HIGH"


class CampaignStatus(str, enum.Enum):
    DRAFT    = "DRAFT"
    ACTIVE   = "ACTIVE"
    PAUSED   = "PAUSED"
    COMPLETE = "COMPLETE"


# ─────────────────────────────────────────────
# CUSTOMERS
# ─────────────────────────────────────────────
class Customer(Base):
    __tablename__ = "customers"

    id            = Column(Integer, primary_key=True, index=True)
    email         = Column(String(255), unique=True, index=True, nullable=False)
    full_name     = Column(String(255), nullable=False)
    phone         = Column(String(50))
    segment       = Column(String(100), default="standard")   # vip / standard / at-risk
    is_active     = Column(Boolean, default=True)
    created_at    = Column(DateTime, default=datetime.utcnow)
    updated_at    = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    transactions  = relationship("Transaction", back_populates="customer")
    feedbacks     = relationship("Feedback",    back_populates="customer")
    churn_scores  = relationship("ChurnScore",  back_populates="customer")
    campaigns     = relationship("CampaignCustomer", back_populates="customer")


# ─────────────────────────────────────────────
# USERS (internal staff / API users)
# ─────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id              = Column(Integer, primary_key=True, index=True)
    email           = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name       = Column(String(255))
    role            = Column(String(50), default="analyst")   # admin / analyst
    is_active       = Column(Boolean, default=True)
    created_at      = Column(DateTime, default=datetime.utcnow)


# ─────────────────────────────────────────────
# TRANSACTIONS
# ─────────────────────────────────────────────
class Transaction(Base):
    __tablename__ = "transactions"

    id              = Column(Integer, primary_key=True, index=True)
    customer_id     = Column(Integer, ForeignKey("customers.id"), nullable=False)
    amount          = Column(Float, nullable=False)
    currency        = Column(String(10), default="USD")
    product_name    = Column(String(255))
    status          = Column(String(50), default="completed")  # completed / refunded / pending
    transaction_ref = Column(String(100), unique=True, index=True)
    created_at      = Column(DateTime, default=datetime.utcnow)

    customer        = relationship("Customer", back_populates="transactions")


# ─────────────────────────────────────────────
# FEEDBACK
# ─────────────────────────────────────────────
class Feedback(Base):
    __tablename__ = "feedback"

    id          = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    score       = Column(Integer, nullable=False)   # 1–5 (NPS / CSAT style)
    category    = Column(String(100))               # product / support / billing
    comment     = Column(Text)
    created_at  = Column(DateTime, default=datetime.utcnow)

    customer    = relationship("Customer", back_populates="feedbacks")


# ─────────────────────────────────────────────
# CHURN SCORES
# ─────────────────────────────────────────────
class ChurnScore(Base):
    __tablename__ = "churn_scores"

    id                   = Column(Integer, primary_key=True, index=True)
    customer_id          = Column(Integer, ForeignKey("customers.id"), nullable=False, unique=True)
    risk_level           = Column(Enum(ChurnRiskLevel), default=ChurnRiskLevel.LOW)
    score                = Column(Float, default=0.0)     # 0.0 – 1.0
    days_since_purchase  = Column(Integer, default=0)
    avg_feedback_score   = Column(Float, default=5.0)
    total_transactions   = Column(Integer, default=0)
    reasoning            = Column(Text)                   # human-readable explanation
    calculated_at        = Column(DateTime, default=datetime.utcnow)

    customer             = relationship("Customer", back_populates="churn_scores")


# ─────────────────────────────────────────────
# CAMPAIGNS
# ─────────────────────────────────────────────
class Campaign(Base):
    __tablename__ = "campaigns"

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String(255), nullable=False)
    description = Column(Text)
    target_risk = Column(Enum(ChurnRiskLevel))           # target HIGH / MEDIUM / LOW risk customers
    status      = Column(Enum(CampaignStatus), default=CampaignStatus.DRAFT)
    created_by  = Column(Integer, ForeignKey("users.id"))
    created_at  = Column(DateTime, default=datetime.utcnow)
    updated_at  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    customers   = relationship("CampaignCustomer", back_populates="campaign")


class CampaignCustomer(Base):
    """Many-to-many: campaigns ↔ customers"""
    __tablename__ = "campaign_customers"

    id          = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    sent_at     = Column(DateTime)
    opened_at   = Column(DateTime)
    converted   = Column(Boolean, default=False)

    campaign    = relationship("Campaign",  back_populates="customers")
    customer    = relationship("Customer",  back_populates="campaigns")
