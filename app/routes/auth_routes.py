import uuid
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
    email: str = Form(...), 
    password: str = Form(...), 
    db: Session = Depends(get_db)
):
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        error_html = '<div id="register-error-message" class="p-4 mb-4 text-sm text-red-800 rounded-lg bg-red-100 dark:bg-red-200 dark:text-red-800"><span class="font-medium">Error!</span> Email already registered.</div>'
        return HTMLResponse(content=error_html)
    
    # Create user
    user_id = str(uuid.uuid4())
    hashed_password = get_password_hash(password)
    new_user = User(id=user_id, email=email, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()

    # Log them in automatically
    access_token = create_access_token(data={"sub": user_id})
    response = HTMLResponse("")
    response.headers["HX-Redirect"] = "/app"
    response.set_cookie(
        key="access_token", 
        value=f"Bearer {access_token}", 
        httponly=True, 
        max_age=604800, # 7 days
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
    user = db.query(User).filter(User.email == email).first()
    error_html = '<div id="login-error-message" class="p-4 mb-4 text-sm text-red-800 rounded-lg bg-red-100 dark:bg-red-200 dark:text-red-800"><span class="font-medium">Error!</span> Invalid email or password.</div>'
    
    if not user:
        return HTMLResponse(content=error_html)
    if not verify_password(password, user.hashed_password):
        return HTMLResponse(content=error_html)

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
