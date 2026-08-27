from fastapi import APIRouter, Request, Depends, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.services.auth_service import AuthService
from app.controllers.deps import get_current_user_optional

router = APIRouter(tags=["Autenticação"])
templates = Jinja2Templates(directory=str(settings.TEMPLATES_DIR))


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, db: Session = Depends(get_db)):
    current_user = get_current_user_optional(request, db)
    if current_user:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(
        request=request,
        name="auth/login.html",
        context={"error": None}
    )


@router.post("/login", response_class=HTMLResponse)
def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    client_ip = request.client.host if request.client else None
    auth_service = AuthService(db)
    success, msg, user = auth_service.authenticate(email, password, ip_address=client_ip)

    if not success or not user:
        return templates.TemplateResponse(
            request=request,
            name="auth/login.html",
            context={"error": msg, "email": email},
            status_code=status.HTTP_400_BAD_REQUEST
        )

    # Criação do token de sessão seguro
    token = AuthService.create_session_token(user.id)
    response = RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        max_age=86400 * 7,
        samesite="lax"
    )
    return response


@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request, db: Session = Depends(get_db)):
    current_user = get_current_user_optional(request, db)
    if current_user:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(
        request=request,
        name="auth/register.html",
        context={"error": None}
    )


@router.post("/register", response_class=HTMLResponse)
def register_submit(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    client_ip = request.client.host if request.client else None
    auth_service = AuthService(db)
    success, msg, user = auth_service.register(name, email, password, ip_address=client_ip)

    if not success or not user:
        return templates.TemplateResponse(
            request=request,
            name="auth/register.html",
            context={"error": msg, "name": name, "email": email},
            status_code=status.HTTP_400_BAD_REQUEST
        )

    # Login automático após cadastro
    token = AuthService.create_session_token(user.id)
    response = RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        max_age=86400 * 7,
        samesite="lax"
    )
    return response


@router.get("/logout")
def logout():
    response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie("session_token")
    return response
