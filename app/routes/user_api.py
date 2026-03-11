from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.db_models import Job

router = APIRouter(prefix="/api/v1/users", tags=["user-jobs"])

@router.get("/{user_id}/jobs")
def get_user_jobs(user_id: str, db: Session = Depends(get_db)):
    jobs = db.query(Job).filter(Job.user_id == user_id).order_by(Job.created_at.desc()).all()
    
    response = []
    for job in jobs:
        job_data = {
            "job_id": job.id,
            "company_name": job.company_name,
            "prompt": job.prompt,
            "status": job.status,
            "created_at": job.created_at,
            "updated_at": job.updated_at,
        }
        if job.status == "completed":
            job_data["download_url"] = f"/api/v1/jobs/{job.id}/download"
        if job.status == "failed":
            job_data["error"] = job.error
            
        response.append(job_data)
        
    return response
