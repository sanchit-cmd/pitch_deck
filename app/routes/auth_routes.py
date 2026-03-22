import uuid
import random
import string
from fastapi import APIRouter, Request, Form, Depends, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.db_models import User
from app.auth import get_password_hash, verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_class=HTMLResponse)
def register(
    request: Request,
    username: str = Form(...),
    email: str = Form(...), 
    password: str = Form(...), 
    db: Session = Depends(get_db)
):
    # Check if existing user by email or username
    existing_user_email = db.query(User).filter(User.email == email).first()
    if existing_user_email:
        error_html = '<div id="register-error-message" class="p-4 mb-4 text-sm text-red-800 rounded-lg bg-red-100 dark:bg-red-200 dark:text-red-800"><span class="font-medium">Error!</span> Email already registered.</div>'
        return HTMLResponse(content=error_html)
        
    existing_user_username = db.query(User).filter(User.username == username).first()
    if existing_user_username:
        error_html = '<div id="register-error-message" class="p-4 mb-4 text-sm text-red-800 rounded-lg bg-red-100 dark:bg-red-200 dark:text-red-800"><span class="font-medium">Error!</span> Username already taken.</div>'
        return HTMLResponse(content=error_html)
    
    # Generate OTP
    otp = ''.join(random.choices(string.digits, k=6))
    print(f"--- OTP FOR {email} IS {otp} ---")
    
    # Create user
    user_id = str(uuid.uuid4())
    hashed_password = get_password_hash(password)
    new_user = User(
        id=user_id, 
        username=username, 
        email=email, 
        hashed_password=hashed_password,
        otp_secret=otp,
        is_verified=False
    )
    db.add(new_user)
    db.commit()

    # Do not log them in automatically. Instead, switch HTMX view to OTP verification form.
    from app.dependencies import templates
    return templates.TemplateResponse("partials/verify_otp_form.html", {"request": request, "email": email})

@router.post("/verify-otp", response_class=HTMLResponse)
def verify_otp(
    request: Request,
    email: str = Form(...),
    otp: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == email).first()
    error_html = '<div id="otp-error-message" class="p-4 mb-4 text-sm text-red-800 rounded-lg bg-red-100 dark:bg-red-200 dark:text-red-800"><span class="font-medium">Error!</span> Invalid OTP. Please try again.</div>'
    
    if not user or user.otp_secret != otp:
        return HTMLResponse(content=error_html)
        
    user.is_verified = True
    user.otp_secret = None
    db.commit()
    
    # Success, create token
    access_token = create_access_token(data={"sub": user.id})
    
    response = HTMLResponse("")
    response.headers["HX-Redirect"] = "/app"
    response.set_cookie(
        key="access_token", 
        value=f"Bearer {access_token}", 
        httponly=True, 
        max_age=604800,
        samesite="lax"
    )
    return response

@router.post("/login", response_class=HTMLResponse)
def login(
    request: Request,
    email: str = Form(...), 
    password: str = Form(...), 
    db: Session = Depends(get_db)
):
    # Enable login with email OR username
    user = db.query(User).filter((User.email == email) | (User.username == email)).first()
    error_html = '<div id="login-error-message" class="p-4 mb-4 text-sm text-red-800 rounded-lg bg-red-100 dark:bg-red-200 dark:text-red-800"><span class="font-medium">Error!</span> Invalid email/username or password.</div>'
    
    if not user:
        return HTMLResponse(content=error_html)
    if not verify_password(password, user.hashed_password):
        return HTMLResponse(content=error_html)
        
    if not user.is_verified:
        # Prompt verification
        from app.dependencies import templates
        return templates.TemplateResponse("partials/verify_otp_form.html", {"request": request, "email": user.email})

    # Success, create token
    access_token = create_access_token(data={"sub": user.id})
    
    response = HTMLResponse("")
    response.headers["HX-Redirect"] = "/app"
    response.set_cookie(
        key="access_token", 
        value=f"Bearer {access_token}", 
        httponly=True, 
        max_age=604800,
        samesite="lax"
    )
    return response

@router.post("/logout")
def logout():
    # Simple redirect to home and clear cookie
    response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    response.delete_cookie(key="access_token")
    return response
