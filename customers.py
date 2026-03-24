"""
Customers Router
  GET    /customers                 list all (paginated)
  POST   /customers                 create
  GET    /customers/at-risk         customers flagged HIGH or MEDIUM churn risk
  GET    /customers/{id}            get one
  PUT    /customers/{id}            update
  DELETE /customers/{id}            soft delete (is_active=False)
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import Customer, User, ChurnScore, ChurnRiskLevel
from app.schemas.schemas import CustomerCreate, CustomerUpdate, CustomerOut, CustomerWithChurn
from app.services.auth_service import get_current_user

router = APIRouter()


@router.get("", response_model=List[CustomerOut])
def list_customers(
    skip:    int = Query(0, ge=0),
    limit:   int = Query(20, ge=1, le=100),
    segment: Optional[str] = None,
    db:      Session = Depends(get_db),
    _:       User    = Depends(get_current_user),
):
    """List all active customers with optional segment filter."""
    q = db.query(Customer).filter(Customer.is_active)
    if segment:
        q = q.filter(Customer.segment == segment)
    return q.offset(skip).limit(limit).all()


@router.post("", response_model=CustomerOut, status_code=201)
def create_customer(
    payload: CustomerCreate,
    db:      Session = Depends(get_db),
    _:       User    = Depends(get_current_user),
):
    """Create a new customer record."""
    if db.query(Customer).filter(Customer.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already exists")

    customer = Customer(**payload.dict())
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


@router.get("/at-risk", response_model=List[CustomerWithChurn])
def at_risk_customers(
    risk_level: Optional[ChurnRiskLevel] = Query(None, description="Filter by risk level"),
    limit:      int = Query(50, ge=1, le=200),
    db:         Session = Depends(get_db),
    _:          User    = Depends(get_current_user),
):
    """
    Return customers with HIGH or MEDIUM churn risk.
    Ordered by risk score descending (worst first).
    """
    q = (
        db.query(Customer, ChurnScore)
        .join(ChurnScore, ChurnScore.customer_id == Customer.id)
        .filter(Customer.is_active)
    )

    if risk_level:
        q = q.filter(ChurnScore.risk_level == risk_level)
    else:
        q = q.filter(ChurnScore.risk_level.in_([ChurnRiskLevel.HIGH, ChurnRiskLevel.MEDIUM]))

    q = q.order_by(ChurnScore.score.desc()).limit(limit)

    results = []
    for customer, churn in q.all():
        data = CustomerWithChurn.from_orm(customer)
        data.churn_risk  = churn.risk_level.value
        data.churn_score = churn.score
        results.append(data)
    return results


@router.get("/{customer_id}", response_model=CustomerOut)
def get_customer(
    customer_id: int,
    db:          Session = Depends(get_db),
    _:           User    = Depends(get_current_user),
):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@router.put("/{customer_id}", response_model=CustomerOut)
def update_customer(
    customer_id: int,
    payload:     CustomerUpdate,
    db:          Session = Depends(get_db),
    _:           User    = Depends(get_current_user),
):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    for field, value in payload.dict(exclude_unset=True).items():
        setattr(customer, field, value)

    db.commit()
    db.refresh(customer)
    return customer


@router.delete("/{customer_id}", status_code=204)
def delete_customer(
    customer_id: int,
    db:          Session = Depends(get_db),
    _:           User    = Depends(get_current_user),
):
    """Soft-delete: sets is_active=False."""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    customer.is_active = False
    db.commit()
