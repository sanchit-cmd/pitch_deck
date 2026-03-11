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

# --- HTMX PARTIAL BUILDERS FOR AUTH ---

@router.get("/auth/login-form", response_class=HTMLResponse)
def get_login_form(request: Request):
    return templates.TemplateResponse("partials/login_form.html", {"request": request})

@router.get("/auth/register-form", response_class=HTMLResponse)
def get_register_form(request: Request):
    return templates.TemplateResponse("partials/register_form.html", {"request": request})
