"""
Churn Risk Engine — core business logic

Rules:
  HIGH   → no purchase ≥ 60 days  AND  avg feedback score < 3
  MEDIUM → no purchase ≥ 30 days  OR   avg feedback score < 3
  LOW    → everything else

Score (0.0 – 1.0) is a weighted composite used for ranking.
"""

from datetime import datetime
from typing import Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.models import Customer, Transaction, Feedback, ChurnScore, ChurnRiskLevel


# ── Thresholds (easy to tune) ────────────────
DAYS_HIGH_RISK   = 60
DAYS_MEDIUM_RISK = 30
SCORE_THRESHOLD  = 3.0      # feedback score below this = negative signal


def calculate_churn_risk(
    customer_id: int, db: Session
) -> Tuple[ChurnRiskLevel, float, int, float, int, str]:
    """
    Returns (risk_level, score, days_since_purchase, avg_feedback, total_transactions, reasoning)
    """
    now = datetime.utcnow()

    # ── Days since last purchase ─────────────
    last_tx = (
        db.query(func.max(Transaction.created_at))
        .filter(Transaction.customer_id == customer_id, Transaction.status == "completed")
        .scalar()
    )
    days_since = (now - last_tx).days if last_tx else 999

    # ── Average feedback score ───────────────
    avg_fb = (
        db.query(func.avg(Feedback.score))
        .filter(Feedback.customer_id == customer_id)
        .scalar()
    )
    avg_feedback = round(float(avg_fb), 2) if avg_fb else 5.0   # default to 5 if no feedback yet

    # ── Total completed transactions ─────────
    total_tx = (
        db.query(func.count(Transaction.id))
        .filter(Transaction.customer_id == customer_id, Transaction.status == "completed")
        .scalar()
    ) or 0

    # ── Business Logic ───────────────────────
    no_recent_60 = days_since >= DAYS_HIGH_RISK
    no_recent_30 = days_since >= DAYS_MEDIUM_RISK
    bad_feedback = avg_feedback < SCORE_THRESHOLD

    reasons = []

    if no_recent_60 and bad_feedback:
        risk_level = ChurnRiskLevel.HIGH
        reasons.append(f"No purchase for {days_since} days (≥{DAYS_HIGH_RISK} threshold)")
        reasons.append(f"Avg feedback {avg_feedback:.1f} is below {SCORE_THRESHOLD}")
    elif no_recent_30 or bad_feedback:
        risk_level = ChurnRiskLevel.MEDIUM
        if no_recent_30:
            reasons.append(f"No purchase for {days_since} days (≥{DAYS_MEDIUM_RISK} threshold)")
        if bad_feedback:
            reasons.append(f"Avg feedback {avg_feedback:.1f} is below {SCORE_THRESHOLD}")
    else:
        risk_level = ChurnRiskLevel.LOW
        reasons.append(f"Active within {days_since} days with good feedback {avg_feedback:.1f}")

    # ── Composite risk score (0.0 – 1.0) ─────
    # Recency component: 0 → just bought, 1 → 120+ days
    recency_score = min(days_since / 120.0, 1.0)

    # Feedback component: 0 → perfect (5), 1 → worst (1)
    feedback_score = max(0.0, (SCORE_THRESHOLD - avg_feedback) / SCORE_THRESHOLD) if avg_feedback < SCORE_THRESHOLD else 0.0

    # Volume bonus: more transactions = lower risk
    volume_bonus = max(0.0, 0.1 - (total_tx * 0.01))

    composite = round(min((recency_score * 0.6) + (feedback_score * 0.35) + volume_bonus, 1.0), 4)

    return risk_level, composite, days_since, avg_feedback, total_tx, "; ".join(reasons)


def upsert_churn_score(customer_id: int, db: Session) -> ChurnScore:
    """Calculate and save/update the churn score for a customer."""
    risk_level, score, days_since, avg_fb, total_tx, reasoning = calculate_churn_risk(customer_id, db)

    existing = db.query(ChurnScore).filter(ChurnScore.customer_id == customer_id).first()

    if existing:
        existing.risk_level          = risk_level
        existing.score               = score
        existing.days_since_purchase = days_since
        existing.avg_feedback_score  = avg_fb
        existing.total_transactions  = total_tx
        existing.reasoning           = reasoning
        existing.calculated_at       = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return existing
    else:
        churn = ChurnScore(
            customer_id          = customer_id,
            risk_level           = risk_level,
            score                = score,
            days_since_purchase  = days_since,
            avg_feedback_score   = avg_fb,
            total_transactions   = total_tx,
            reasoning            = reasoning,
        )
        db.add(churn)
        db.commit()
        db.refresh(churn)
        return churn


def recalculate_all(db: Session) -> int:
    """Recalculate churn scores for every active customer. Returns count updated."""
    customers = db.query(Customer).filter(Customer.is_active).all()
    for c in customers:
        upsert_churn_score(c.id, db)
    return len(customers)
