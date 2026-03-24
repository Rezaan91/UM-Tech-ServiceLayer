"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-03-10 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("email", sa.String(255), unique=True, index=True, nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255)),
        sa.Column("role", sa.String(50), server_default="analyst"),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    op.create_table(
        "customers",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("email", sa.String(255), unique=True, index=True, nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(50)),
        sa.Column("segment", sa.String(100), server_default="standard"),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    op.create_table(
        "transactions",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(10), server_default="USD"),
        sa.Column("product_name", sa.String(255)),
        sa.Column("status", sa.String(50), server_default="completed"),
        sa.Column("transaction_ref", sa.String(100), unique=True, index=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    op.create_table(
        "feedback",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(100)),
        sa.Column("comment", sa.Text()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    op.create_table(
        "churn_scores",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id"), nullable=False, unique=True),
        sa.Column("risk_level", sa.Enum("LOW", "MEDIUM", "HIGH", name="churnrisklevel"), server_default="LOW"),
        sa.Column("score", sa.Float(), server_default="0.0"),
        sa.Column("days_since_purchase", sa.Integer(), server_default="0"),
        sa.Column("avg_feedback_score", sa.Float(), server_default="5.0"),
        sa.Column("total_transactions", sa.Integer(), server_default="0"),
        sa.Column("reasoning", sa.Text()),
        sa.Column("calculated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    op.create_table(
        "campaigns",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("target_risk", sa.Enum("LOW", "MEDIUM", "HIGH", name="churnrisklevel"), nullable=True),
        sa.Column("status", sa.Enum("DRAFT", "ACTIVE", "PAUSED", "COMPLETE", name="campaignstatus"), server_default="DRAFT"),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    op.create_table(
        "campaign_customers",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("campaign_id", sa.Integer(), sa.ForeignKey("campaigns.id"), nullable=False),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("sent_at", sa.DateTime()),
        sa.Column("opened_at", sa.DateTime()),
        sa.Column("converted", sa.Boolean(), server_default="false"),
    )


def downgrade() -> None:
    op.drop_table("campaign_customers")
    op.drop_table("campaigns")
    op.drop_table("churn_scores")
    op.drop_table("feedback")
    op.drop_table("transactions")
    op.drop_table("customers")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS churnrisklevel")
    op.execute("DROP TYPE IF EXISTS campaignstatus")
