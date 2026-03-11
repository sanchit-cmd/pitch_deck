from sqlalchemy import Column, String, Integer, Text, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime, timezone

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    jobs = relationship("Job", back_populates="user")


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), index=True, nullable=True)
    user = relationship("User", back_populates="jobs")
    company_name = Column(String, index=True)
    prompt = Column(Text)
    num_slides = Column(Integer)
    prefered_tone = Column(String)
    
    # pending, processing, completed, failed
    status = Column(String, default="pending", index=True) 
    error = Column(Text, nullable=True)
    
    # Store the entire final LangGraph raw state (dict->json)
    result_data = Column(JSON, nullable=True)
    
    # Path to the completed pdf path
    pdf_path = Column(String, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
