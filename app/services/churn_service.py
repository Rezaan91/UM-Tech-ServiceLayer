DAYS_HIGH_RISK = 60
DAYS_MEDIUM_RISK = 30
SCORE_THRESHOLD = 3.0

def calculate_churn_risk_stub(customer_id: int, db=None):
    # Minimal deterministic churn result for tests
    return ("LOW", 0.0, 0, 5.0, 0, "No risk - stubbed")
