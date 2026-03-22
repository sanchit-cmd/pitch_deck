import uuid
import base64
from typing import Optional, Literal
from fastapi import APIRouter, Request, Form, BackgroundTasks, UploadFile, File, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage

from app.database import get_db
from app.models.db_models import Job, User
from app.auth import get_current_user
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
    user: User = Depends(get_current_user)
):
    if not user or user.credits < 1:
        return templates.TemplateResponse("partials/job_error.html", {"request": request, "error_message": "Insufficient credits. Please purchase more credits to generate a Pitch Deck."})
    logo_base64 = None
    logo_mime_type = None
    if logo_file and logo_file.filename:
        content = await logo_file.read()
        logo_base64 = base64.b64encode(content).decode("utf-8")
        logo_mime_type = logo_file.content_type or "image/png"

    job_id = str(uuid.uuid4())
    
    new_job = Job(
        id=job_id,
        user_id=user.id,
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
        user_id=user.id,
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

@router.post("/enhance-prompt", response_class=HTMLResponse)
async def enhance_prompt(
    request: Request, 
    prompt: Optional[str] = Form(None), 
    user: User = Depends(get_current_user)
):
    if not prompt or len(prompt.strip()) < 5:
        enhanced = prompt or ""
    else:
        try:
            llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.7)
            sys_msg = SystemMessage(content="You are an expert startup pitch deck copywriter. Enhance the user's raw business idea or prompt into a highly cohesive, descriptive, and investor-ready paragraph (around 3-5 sentences) that covers the core problem, solution, and value proposition. Output ONLY the rewritten text, with no markdown formatting or intro/outro.")
            human = HumanMessage(content=prompt)
            res = llm.invoke([sys_msg, human])
            enhanced = res.content.strip()
        except Exception as e:
            print(f"Enhancement Error: {e}")
            enhanced = prompt # Fallback
            
    html = f'''<textarea id="prompt" name="prompt" rows="5" required class="block w-full px-4 py-3 bg-white/50 dark:bg-gray-900/50 border border-gray-200 dark:border-gray-700 rounded-xl shadow-sm placeholder-gray-400 focus:ring-2 focus:ring-brand-500 focus:border-brand-500 transition-all text-sm font-medium text-gray-900 dark:text-white resize-y" placeholder="E.g. We are building an AI agent that automates customer support for e-commerce companies utilizing fine-tuned LLMs...">{enhanced}</textarea>'''
    return HTMLResponse(content=html)
