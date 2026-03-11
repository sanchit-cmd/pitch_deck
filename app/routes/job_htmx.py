import uuid
import base64
from typing import Optional, Literal
from fastapi import APIRouter, Request, Form, BackgroundTasks, UploadFile, File, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.db_models import Job, User
from app.auth import get_current_user_optional
from app.schemas.job import JobRequest
from app.services.job_service import process_pitch_deck
from app.dependencies import templates

router = APIRouter(prefix="/htmx/jobs", tags=["htmx-jobs"])

@router.post("", response_class=HTMLResponse)
async def create_htmx_job(
    request: Request,
    background_tasks: BackgroundTasks,
    company_name: str = Form(...),
    prompt: str = Form(...),
    num_slides: int = Form(10),
    prefered_tone: Literal["MINIMAL", "BOLD", "CORPORATE", "FUN"] = Form(...),
    logo_file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional)
):
    logo_base64 = None
    logo_mime_type = None
    if logo_file and logo_file.filename:
        content = await logo_file.read()
        logo_base64 = base64.b64encode(content).decode("utf-8")
        logo_mime_type = logo_file.content_type or "image/png"

    job_id = str(uuid.uuid4())
    
    new_job = Job(
        id=job_id,
        user_id=user.id if user else None,
        company_name=company_name,
        prompt=prompt,
        num_slides=num_slides,
        prefered_tone=prefered_tone,
        status="pending"
    )
    db.add(new_job)
    db.commit()

    # Create JobRequest for the background worker
    job_req = JobRequest(
        user_id=user.id if user else None,
        company_name=company_name,
        prompt=prompt,
        num_slides=num_slides,
        prefered_tone=prefered_tone,
        logo_base64=logo_base64,
        logo_mime_type=logo_mime_type
    )
    
    background_tasks.add_task(process_pitch_deck, job_id, job_req)
    # Return the loading partial so HTMX can start polling
    return templates.TemplateResponse("partials/job_loading.html", {"request": request, "job_id": job_id})

@router.get("/{job_id}/status", response_class=HTMLResponse)
def get_htmx_job_status(job_id: str, request: Request, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        return templates.TemplateResponse("partials/job_error.html", {"request": request, "error_message": "Job not found"})
    
    if job.status == "completed":
        return templates.TemplateResponse("partials/job_success.html", {"request": request, "job_id": job_id})
    elif job.status == "failed":
        return templates.TemplateResponse("partials/job_error.html", {"request": request, "error_message": job.error or "Pipeline failed"})
    
    # pending or processing
    return templates.TemplateResponse("partials/job_loading.html", {"request": request, "job_id": job_id})
