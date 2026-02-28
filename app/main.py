import uuid
from typing import Dict, Any, Optional, Literal
from fastapi import FastAPI, BackgroundTasks, HTTPException, Request, Form, UploadFile, File
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import base64

from app.models.input_model import InputFormat
from app.prompts.planner_prompt import generate_planner_agent_prompt
from app.state import DeckState

from app.workflow import graph

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup Jinja2 templates directory
templates_dir = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=templates_dir)


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


def cleanup_job(job_id: str, pdf_path: str):
    """Deletes job artifacts from disk and memory to prevent leaks."""
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

    # 3. Delete from in-memory dictionary
    if job_id in jobs:
        del jobs[job_id]


@app.get("/api/v1/jobs/{job_id}/download")
def download_pdf(job_id: str, background_tasks: BackgroundTasks):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job_data = jobs[job_id]

    if job_data["status"] != "completed":
        raise HTTPException(status_code=400, detail="Job is not completed yet")

    pdf_path = job_data.get("pdf_path")
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


# --- HTML UI Routes ---

@app.get("/")
async def ui_home(request: Request):
    """Renders the HTML form for starting a pitch deck job."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/submit")
async def ui_submit(
    request: Request,
    background_tasks: BackgroundTasks,
    company_name: str = Form(...),
    tagline: str = Form(...),
    problem: str = Form(...),
    solution: str = Form(...),
    target_customer: str = Form(...),
    industry: str = Form(...),
    business_model: str = Form(...),
    stage: Literal["MVP", "IDEA", "SALES"] = Form(...),
    goal_of_deck: Literal["SALES", "COLLEGE_PROJECT", "INVESTOR"] = Form(...),
    competitors: str = Form(...),
    unique_advantage: str = Form(...),
    prefered_tone: Literal["MINIMAL", "BOLD", "CORPORATE", "FUN"] = Form(...),
    logo: UploadFile = File(None)
):
    """Receives the form, creates a job, and redirects to the status page."""
    logo_base_64 = None
    logo_mime = None
    if logo and logo.filename:
        content = await logo.read()
        if content:
            logo_base_64 = base64.b64encode(content).decode('utf-8')
            logo_mime = logo.content_type

    job_req = JobRequest(
        company_name=company_name,
        tagline=tagline,
        problem=problem,
        solution=solution,
        target_customer=target_customer,
        industry=industry,
        business_model=business_model,
        stage=stage,
        goal_of_deck=goal_of_deck,
        competitors=competitors,
        unique_advantage=unique_advantage,
        prefered_tone=prefered_tone,
        logo_base64=logo_base_64,
        logo_mime_type=logo_mime,
    )

    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "pending"}
    background_tasks.add_task(process_pitch_deck, job_id, job_req)

    # Redirect to the status view page using a 303 See Other
    return RedirectResponse(url=f"/status/{job_id}", status_code=303)


@app.get("/status/{job_id}")
async def ui_status(request: Request, job_id: str):
    """Renders the status polling page."""
    # We will let the template load first, then ping the API, avoiding erroring here if possible
    # But checking if exists is alright natively
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    return templates.TemplateResponse(
        "status.html", {"request": request, "job_id": job_id}
    )
