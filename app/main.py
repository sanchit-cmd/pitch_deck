import base64
import uuid
from typing import Dict, Any, Optional, Literal
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.models.input_model import InputFormat
from app.prompts.planner_prompt import generate_planner_agent_prompt
from app.state import DeckState

from app.workflow import graph

app = FastAPI()


class JobRequest(BaseModel):
    company_name: str
    tagline: str
    problem: str
    solution: str
    target_customer: str
    industry: str
    business_model: str
    stage: Literal["MVP", "IDEA", "SALES"]
    goal_of_deck: Literal["SALES", "COLLEGE_PROJECT", "INVESTOR"]
    competitors: str
    unique_advantage: str
    prefered_tone: Literal["MINIMAL", "BOLD", "CORPORATE", "FUN"]
    logo_base64: Optional[str] = None  # Expected to be pure base64 string
    logo_mime_type: Optional[str] = "image/png"


# In-memory storage for jobs (for prototyping)
jobs: Dict[str, Dict[str, Any]] = {}


def process_pitch_deck(job_id: str, request: JobRequest):
    jobs[job_id]["status"] = "processing"
    
    try:
        test_input: InputFormat = {
            "company_name": request.company_name,
            "tagline": request.tagline,
            "problem": request.problem,
            "solution": request.solution,
            "target_customer": request.target_customer,
            "industry": request.industry,
            "business_model": request.business_model,
            "stage": request.stage,
            "competitors": request.competitors,
            "unique_advantage": request.unique_advantage,
            "prefered_tone": request.prefered_tone,
            "goal_of_deck": request.goal_of_deck,
        }

        logo_data = None
        if request.logo_base64:
            logo_data = {"data": request.logo_base64, "mime_type": request.logo_mime_type}

        raw_input = generate_planner_agent_prompt(
            test_input, 
            logo_base64=logo_data["data"] if logo_data else None
        )

        test_deck: DeckState = {
            "raw_prompt": raw_input,
        }

        if logo_data:
            test_deck["logo"] = logo_data

        config = {"configurable": {"thread_id": job_id}}
        response = graph.invoke(test_deck, config=config)
        
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["result"] = response
        
        # Store PDF path explicitly for easy retrieval
        if "pdf_path" in response:
            jobs[job_id]["pdf_path"] = response["pdf_path"]
        
    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)


@app.post("/api/v1/jobs")
def create_job(request: JobRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "pending"}
    background_tasks.add_task(process_pitch_deck, job_id, request)
    return {"job_id": job_id}


@app.get("/api/v1/jobs/{job_id}")
def get_job_status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # We strip out the raw result and pdf path from the status API to keep it clean, 
    # but include a download URL if ready
    response = {"status": jobs[job_id]["status"]}
    
    if jobs[job_id]["status"] == "failed":
        response["error"] = jobs[job_id].get("error")
        
    if jobs[job_id]["status"] == "completed":
        response["download_url"] = f"/api/v1/jobs/{job_id}/download"
        
    return response


@app.get("/api/v1/jobs/{job_id}/download")
def download_pdf(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
        
    job_data = jobs[job_id]
    
    if job_data["status"] != "completed":
        raise HTTPException(status_code=400, detail="Job is not completed yet")
        
    pdf_path = job_data.get("pdf_path")
    if not pdf_path:
         raise HTTPException(status_code=404, detail="PDF generation failed or missing")
         
    return FileResponse(
        path=pdf_path, 
        filename=f"pitch_deck_{job_id}.pdf", 
        media_type="application/pdf"
    )
