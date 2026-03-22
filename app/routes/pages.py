from typing import Optional
from fastapi import APIRouter, Request, Depends, status
from fastapi.responses import HTMLResponse, RedirectResponse

from app.dependencies import templates
from app.models.db_models import User
from app.auth import get_current_user_optional, get_current_user

router = APIRouter()

# --- FRONTEND HTML ROUTES ---

@router.get("/", response_class=HTMLResponse)
def root(request: Request, user: Optional[User] = Depends(get_current_user_optional)):
    return templates.TemplateResponse("home.html", {"request": request, "user": user})

@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, user: Optional[User] = Depends(get_current_user_optional)):
    if user:
        return RedirectResponse(url="/app", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse("login.html", {"request": request, "user": user})

@router.get("/app", response_class=HTMLResponse)
def app_page(request: Request, user: User = Depends(get_current_user)):
    return templates.TemplateResponse("app.html", {"request": request, "user": user})

@router.get("/profile", response_class=HTMLResponse)
def profile_page(request: Request, user: User = Depends(get_current_user)):
    # Jobs are lazy loaded if relationship is setup, but let's just use it
    jobs = sorted(user.jobs, key=lambda x: x.created_at, reverse=True)
    return templates.TemplateResponse("profile.html", {"request": request, "user": user, "jobs": jobs})

@router.get("/pricing", response_class=HTMLResponse)
def pricing_page(request: Request, user: User = Depends(get_current_user)):
    from app.routes.billing import RAZORPAY_KEY_ID
    return templates.TemplateResponse("pricing.html", {
        "request": request, 
        "user": user,
        "razorpay_key_id": RAZORPAY_KEY_ID
    })

# --- HTMX PARTIAL BUILDERS FOR AUTH ---

@router.get("/auth/login-form", response_class=HTMLResponse)
def get_login_form(request: Request):
    return templates.TemplateResponse("partials/login_form.html", {"request": request})

@router.get("/auth/register-form", response_class=HTMLResponse)
def get_register_form(request: Request):
    return templates.TemplateResponse("partials/register_form.html", {"request": request})
