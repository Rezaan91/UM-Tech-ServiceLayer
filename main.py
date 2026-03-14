"""
UM Tech ServiceLayer - Customer Retention & Churn Risk API
Main application entry point
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from alembic.config import Config
from alembic import command

from app.routers import auth, customers, transactions, feedback, churn, campaigns


def run_migrations():
    """Run Alembic migrations on startup — resolves paths correctly inside Docker."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    alembic_cfg = Config(os.path.join(base_dir, "alembic.ini"))
    alembic_cfg.set_main_option("script_location", os.path.join(base_dir, "migrations"))
    command.upgrade(alembic_cfg, "head")


app = FastAPI(
    title="UM Tech ServiceLayer",
    description="Customer Retention & Churn Risk API — Transaction → Review → Data → Campaign → Retention",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


@app.on_event("startup")
def startup_event():
    run_migrations()


# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router,         prefix="/auth",         tags=["Authentication"])
app.include_router(customers.router,    prefix="/customers",    tags=["Customers"])
app.include_router(transactions.router, prefix="/transactions", tags=["Transactions"])
app.include_router(feedback.router,     prefix="/feedback",     tags=["Feedback"])
app.include_router(churn.router,        prefix="/churn",        tags=["Churn Scores"])
app.include_router(campaigns.router,    prefix="/campaigns",    tags=["Campaigns"])


@app.get("/", tags=["Health"])
def root():
    return {
        "service": "UM Tech ServiceLayer",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "healthy"}
