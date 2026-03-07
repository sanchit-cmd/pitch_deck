import uuid
from typing import Dict, Any, Optional, Literal
from fastapi import FastAPI, BackgroundTasks, HTTPException, Request, Form, UploadFile, File
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import base64
from fastapi.staticfiles import StaticFiles

# Setup React static files directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend", "out")

from app.models.input_model import InputFormat
from app.prompts.planner_prompt import generate_planner_agent_prompt
from app.state import DeckState
from app.agents.generator_agent import generate_single_image
from app.agents.pdf_agent import pdf_generator
from app.workflow import graph

from sqlalchemy.orm import Session
from fastapi import Depends
from app.database import engine, Base, get_db
from app.models.db_models import Job

# Create database tables if they do not exist
Base.metadata.create_all(bind=engine)

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



class JobRequest(BaseModel):
    company_name: str
    prompt: str
    num_slides: Optional[int] = 10
    prefered_tone: Literal["MINIMAL", "BOLD", "CORPORATE", "FUN"]
    logo_base64: Optional[str] = None  # Expected to be pure base64 string
    logo_mime_type: Optional[str] = "image/png"

class RegenerateRequest(BaseModel):
    new_prompt: Optional[str] = None

# Background task: needs its own distinct DB session since it runs out of request scope
def process_pitch_deck(job_id: str, request: JobRequest):
    # Retrieve a fresh local session for the background thread
    from app.database import SessionLocal
    db = SessionLocal()
    
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return
            
        job.status = "processing"
        db.commit()

        test_input: InputFormat = {
            "company_name": request.company_name,
            "prompt": request.prompt,
            "prefered_tone": request.prefered_tone,
            "num_slides": request.num_slides,
        }

        logo_data = None
        if request.logo_base64:
            logo_data = {
                "data": request.logo_base64,
                "mime_type": request.logo_mime_type,
            }

        raw_input = generate_planner_agent_prompt(
            test_input, logo_base64=logo_data["data"] if logo_data else None
        )

        test_deck: DeckState = {
            "raw_prompt": raw_input,
            "job_id": job_id,
        }

        if logo_data:
            test_deck["logo"] = logo_data

        config = {"configurable": {"thread_id": job_id}}
        response = graph.invoke(test_deck, config=config)
        job.status = "completed"
        job.result_data = response

        # Store PDF path explicitly for easy retrieval
        if "pdf_path" in response:
            job.pdf_path = response["pdf_path"]
            
        db.commit()

    except Exception as e:
        job.status = "failed"
        job.error = str(e)
        db.commit()
    finally:
        db.close()


@app.post("/api/v1/jobs")
def create_job(request: JobRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    job_id = str(uuid.uuid4())
    
    new_job = Job(
        id=job_id,
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


@app.get("/api/v1/jobs/{job_id}")
def get_job_status(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # We strip out the raw result and pdf path from the status API to keep it clean,
    # but include a download URL if ready
    response = {"status": job.status}

    if job.status == "failed":
        response["error"] = job.error

    if job.status == "completed":
        response["download_url"] = f"/api/v1/jobs/{job_id}/download"

    return response


@app.get("/api/v1/jobs/{job_id}/details")
def get_job_details(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    if job.status != "completed":
        raise HTTPException(status_code=400, detail="Job is not completed yet")
        
    result_state = job.result_data or {}
    
    return {
        "status": job.status,
        "download_url": f"/api/v1/jobs/{job_id}/download",
        "slides": result_state.get("slide_images", [])
    }


def cleanup_job(job_id: str, pdf_path: str):
    """Deletes job artifacts from disk to prevent leaks."""
    import shutil

    # 1. Delete generated slide images directory
    image_dir = Path(f"./slides_images/{job_id}/")
    if image_dir.exists():
        shutil.rmtree(image_dir, ignore_errors=True)

    # 2. Delete the PDF file and its directory
    pdf_file_path = Path(pdf_path)
    if pdf_file_path.exists():
        pdf_file_path.unlink()

    pdf_dir = Path(f"./pdfs/{job_id}/")
    if pdf_dir.exists():
        try:
            pdf_dir.rmdir()
        except OSError:
            pass  # might not be empty if something went wrong, safe to ignore


@app.get("/api/v1/jobs/{job_id}/download")
def download_pdf(job_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != "completed":
        raise HTTPException(status_code=400, detail="Job is not completed yet")

    pdf_path = job.pdf_path
    if not pdf_path:
        raise HTTPException(status_code=404, detail="PDF generation failed or missing")

    # Schedule cleanup to run AFTER the response has been successfully sent
    background_tasks.add_task(cleanup_job, job_id, pdf_path)

    return FileResponse(
        path=pdf_path,
        filename=f"pitch_deck_{job_id}.pdf",
        media_type="application/pdf",
        content_disposition_type="attachment",
    )


from pathlib import Path


# --- API Endpoints for Single Slide Edit / Regenerate ---

@app.post("/api/v1/jobs/{job_id}/slides/{slide_number}/regenerate")
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
        import copy
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

# --- Serve Frontend Assets ---

# Mount the static _next assets and files explicitly
if os.path.exists(FRONTEND_DIR):
    app.mount("/_next", StaticFiles(directory=os.path.join(FRONTEND_DIR, "_next")), name="next_assets")
    
    # Needs to serve images that were put in slides_images directly at root paths if Next expects it, but we can do it manually:
    app.mount("/slides_images", StaticFiles(directory=os.path.join(BASE_DIR, "slides_images")), name="slides_images")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        # Serve exact file if it exists, otherwise fallback to React index.html for CSR
        requested_path = os.path.join(FRONTEND_DIR, full_path)
        
        # If the path points to an existing file, return it
        if os.path.isfile(requested_path):
            return FileResponse(requested_path)
            
        # If it's a directory, next.js might have an index.html or index.txt inside it
        if os.path.isdir(requested_path):
            # If the request specifically expects text/x-component (RSC), return .txt
            index_txt = os.path.join(requested_path, "index.txt")
            if os.path.isfile(index_txt) and full_path.endswith('.txt'):
                return FileResponse(index_txt)
                
            index_file = os.path.join(requested_path, "index.html")
            if os.path.isfile(index_file):
                return FileResponse(index_file)
            
        # Check if there's a specific .html or .txt file for this path (next export behavior)
        if os.path.isfile(requested_path + ".html"):
            return FileResponse(requested_path + ".html")
            
        if os.path.isfile(requested_path + ".txt"):
            return FileResponse(requested_path + ".txt")
            
        # Otherwise, assume it's a client side route and serve the root generic index
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))
