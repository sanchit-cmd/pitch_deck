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


@router.post("/{job_id}/publish", response_class=HTMLResponse)
async def publish_deck(job_id: str, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == user.id).first()
    if not job:
        return HTMLResponse("Job not found", status_code=404)
        
    from app.agents.pdf_agent import pdf_generator
    
    # Run the pdf generator manually against the state
    state = {
        "job_id": job.id,
        "slide_images": job.result_data.get("slide_images", [])
    }
    updated_state = pdf_generator(state)
    
    if updated_state.get("pdf_path"):
        job.pdf_path = updated_state["pdf_path"]
        db.commit()
    
    html = f'''
    <div id="publish-status" class="flex items-center text-sm font-bold text-green-600 bg-green-50 px-4 py-2 rounded-xl border border-green-200 shadow-sm animate-fade-in">
        <svg class="w-4 h-4 mr-2 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>
        Published! <a href="/api/v1/jobs/{job.id}/download" target="_blank" class="ml-4 flex items-center text-white bg-green-600 hover:bg-green-700 transition-colors px-3 py-1.5 rounded-lg shadow-sm whitespace-nowrap"><svg class="w-3 h-3 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path></svg> Download PDF</a>
    </div>
    '''
    return HTMLResponse(content=html)


@router.post("/{job_id}/slide/{slide_number}/regenerate", response_class=HTMLResponse)
async def regenerate_slide(
    job_id: str, 
    slide_number: int,
    request: Request,
    title: str = Form(...),
    content_bullets: str = Form(...),
    visual_description: str = Form(""),
    layout_description: str = Form(""),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == user.id).first()
    if not job:
        return HTMLResponse("Job not found", status_code=404)
        
    # Get the slide plan
    slide_plan = job.result_data.get("slide_plan", {})
    slides = slide_plan.get("slides", [])
    
    target_slide = None
    slide_index = -1
    for i, s in enumerate(slides):
        if s["slide_number"] == slide_number:
            target_slide = s
            slide_index = i
            break
            
    if not target_slide:
        return HTMLResponse("Slide not found", status_code=404)
        
    # Update slide
    target_slide["title"] = title
    target_slide["content_bullets"] = content_bullets
    target_slide["visual_description"] = visual_description
    target_slide["layout_description"] = layout_description
    
    slides[slide_index] = target_slide
    job.result_data["slide_plan"]["slides"] = slides
    
    # Generate prompt
    from app.prompts.generator_prompt import generate_slide_prompt
    logo_data = job.result_data.get("logo")
    
    new_prompt = generate_slide_prompt(
        overall_style=slide_plan.get("overall_style", ""),
        visual_mood=slide_plan.get("visual_mood", ""),
        color_palette=slide_plan.get("color_palette", ""),
        slide_state=target_slide,
        logo_base64=logo_data["data"] if logo_data else None
    )
    
    # Create the slide prompt object
    slide_prompt_obj = {
        "slide_number": slide_number,
        "prompt": new_prompt,
        "slide_type": target_slide["slide_type"]
    }
    
    # Generate image
    from app.agents.generator_agent import generate_single_image
    result = generate_single_image(slide_prompt_obj, job.id, logo_data)
    
    # Update slide_images array
    slide_images = job.result_data.get("slide_images", [])
    for idx, img in enumerate(slide_images):
        if img["slide_number"] == slide_number:
            slide_images[idx] = result
            break
    else:
        slide_images.append(result)
        
    job.result_data["slide_images"] = slide_images
    
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(job, "result_data")
    db.commit()
    
    # We construct the exact replacement for the main canvas, and OOB swap the thumbnail
    img_url = "/" + result["image_path"] if result.get("image_path") else ""
    rand_t = uuid.uuid4().hex[:8]
    
    html = f'''
    <div id="main-img-{slide_number}" class="w-full relative pt-[56.25%] bg-gray-50 dark:bg-gray-900">
        <img src="{img_url}?t={rand_t}" class="absolute inset-0 w-full h-full object-contain">
        <div class="htmx-indicator absolute inset-0 bg-gray-900/90 backdrop-blur-md flex-col items-center justify-center z-50">
            <svg class="w-12 h-12 animate-spin text-brand-500 mb-4" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
            <p class="text-white font-bold text-lg tracking-wide animate-pulse">Running AI Generator...</p>
            <p class="text-gray-400 text-xs mt-2">Connecting to Gemini & Image Synthesis Pipelines</p>
        </div>
    </div>
    
    <div id="thumb-{slide_number}" hx-swap-oob="true" class="relative pt-[56.25%] bg-gray-200 dark:bg-gray-900 border-b border-gray-200/50 dark:border-gray-700">
        <img src="{img_url}?t={rand_t}" class="absolute inset-0 w-full h-full object-cover">
    </div>
    '''
    
    return HTMLResponse(content=html)
