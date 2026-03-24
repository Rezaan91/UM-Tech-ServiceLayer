import uuid

from sqlalchemy import Column, ForeignKey, String

from app.core.database import Base


class Assessment(Base):
    __tablename__ = "assessments"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id = Column(String, ForeignKey("customers.id"))
    status = Column(String, default="draft")
