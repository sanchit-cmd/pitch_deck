import uuid
from typing import Optional
from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import copy

from app.database import get_db
from app.models.db_models import Job
from app.schemas.job import JobRequest, RegenerateRequest
from app.services.job_service import process_pitch_deck, cleanup_job
from app.agents.generator_agent import generate_single_image
from app.agents.pdf_agent import pdf_generator
from app.models.db_models import User
from app.auth import get_current_user

router = APIRouter(prefix="/api/v1/jobs", tags=["api-jobs"])

@router.post("")
def create_job(request: JobRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    job_id = str(uuid.uuid4())
    
    new_job = Job(
        id=job_id,
        user_id=request.user_id,
        company_name=request.company_name,
        prompt=request.prompt,
        num_slides=request.num_slides,
        prefered_tone=request.prefered_tone,
        status="pending"
    )
    db.add(new_job)
    db.commit()
    
    # Send to background worker queue
    background_tasks.add_task(process_pitch_deck, job_id, request)
    return {"job_id": job_id}


@router.get("/{job_id}")
def get_job_status(job_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job or job.user_id != user.id:
        raise HTTPException(status_code=404, detail="Job not found")

    response = {"status": job.status}

    if job.status == "failed":
        response["error"] = job.error

    if job.status == "completed":
        response["download_url"] = f"/api/v1/jobs/{job_id}/download"

    return response


@router.get("/{job_id}/details")
def get_job_details(job_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job or job.user_id != user.id:
        raise HTTPException(status_code=404, detail="Job not found")
        
    if job.status != "completed":
        raise HTTPException(status_code=400, detail="Job is not completed yet")
        
    result_state = job.result_data or {}
    
    return {
        "status": job.status,
        "download_url": f"/api/v1/jobs/{job_id}/download",
        "slides": result_state.get("slide_images", [])
    }


@router.get("/{job_id}/download")
def download_pdf(job_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job or job.user_id != user.id:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != "completed":
        raise HTTPException(status_code=400, detail="Job is not completed yet")

    pdf_path = job.pdf_path
    if not pdf_path:
        raise HTTPException(status_code=404, detail="PDF generation failed or missing")
        
    if not job.is_downloaded:
        if user.credits < 1:
            raise HTTPException(status_code=402, detail="Insufficient credits to download this presentation")
        
        user.credits -= 1
        job.is_downloaded = True
        db.commit()

    # Schedule cleanup to run AFTER the response has been successfully sent
    background_tasks.add_task(cleanup_job, job_id, pdf_path)

    return FileResponse(
        path=pdf_path,
        filename=f"pitch_deck_{job_id}.pdf",
        media_type="application/pdf",
        content_disposition_type="attachment",
    )


@router.post("/{job_id}/slides/{slide_number}/regenerate")
def regenerate_slide(job_id: str, slide_number: int, request: RegenerateRequest, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != "completed":
        raise HTTPException(status_code=400, detail="Job is not completed yet")

    result_state = job.result_data
    if not result_state or "slide_prompt" not in result_state:
        raise HTTPException(status_code=500, detail="Job state invalid or missing prompts")

    # Find the specific slide prompt
    slide_prompts = result_state["slide_prompt"]
    target_prompt = None
    for sp in slide_prompts:
        if sp["slide_number"] == slide_number:
            target_prompt = sp
            break

    if not target_prompt:
        raise HTTPException(status_code=404, detail=f"Slide {slide_number} not found in this deck")

    if request.new_prompt:
        # Append user edits/instructions to the prompt for the generator
        target_prompt["prompt"] += f"\n\nUSER EDITS: {request.new_prompt}"

    logo = result_state.get("logo")

    try:
        # Re-run generator for this single slide
        image_result = generate_single_image(target_prompt, job_id, logo)

        if not image_result or not image_result.get("image_path"):
            raise HTTPException(status_code=500, detail="Failed to regenerate image")

        # Update the state with the new image
        for idx, img in enumerate(result_state["slide_images"]):
            if img["slide_number"] == slide_number:
                result_state["slide_images"][idx] = image_result
                break

        # Re-generate the full PDF with the new replaced slip
        # We need to copy because SQLAlchemy might not track deep mutations to JSON columns
        updated_state = copy.deepcopy(result_state)
        new_state = pdf_generator(updated_state)
        
        # Save updated state
        job.result_data = new_state
        job.pdf_path = new_state.get("pdf_path")
        db.commit()

        return {
            "status": "success", 
            "slide_number": slide_number, 
            "image_path": image_result["image_path"],
            "download_url": f"/api/v1/jobs/{job_id}/download"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
