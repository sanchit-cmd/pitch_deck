from sqlalchemy import Column, String, Integer, Text, DateTime, JSON
from app.database import Base
from datetime import datetime, timezone

class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=True) # Added for Clerk authentication tracking
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
