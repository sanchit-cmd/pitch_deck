import os
from pathlib import Path
from typing import Dict, Any
from app.database import SessionLocal
from app.models.db_models import Job
from app.schemas.job import JobRequest
from app.models.input_model import InputFormat
from app.prompts.planner_prompt import generate_planner_agent_prompt
from app.state import DeckState
from app.workflow import graph

def process_pitch_deck(job_id: str, request: JobRequest):
    # Retrieve a fresh local session for the background thread
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
