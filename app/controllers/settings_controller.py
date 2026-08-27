from fastapi import APIRouter, Request, Depends, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.models.user import User
from app.controllers.deps import require_auth_user
from app.services.email_service import EmailService
from app.services.auth_service import AuthService
from app.models.email_account import SmtpSecurity

router = APIRouter(tags=["Configurações"])
templates = Jinja2Templates(directory=str(settings.TEMPLATES_DIR))


@router.get("/settings/email", response_class=HTMLResponse)
def email_settings_view(
    request: Request,
    test_result: str = None,
    test_success: str = None,
    current_user: User = Depends(require_auth_user),
    db: Session = Depends(get_db)
):
    email_service = EmailService(db)
    smtp_account = email_service.get_smtp_account(current_user.id)

    return templates.TemplateResponse(
        request=request,
        name="settings/smtp.html",
        context={
            "user": current_user,
            "account": smtp_account,
            "test_result": test_result,
            "test_success": test_success == "1" if test_success else None,
            "error": None,
            "active_menu": "settings_email"
        }
    )


@router.post("/settings/email", response_class=HTMLResponse)
def save_email_settings(
    request: Request,
    sender_name: str = Form(...),
    email: str = Form(...),
    smtp_host: str = Form(...),
    smtp_port: int = Form(...),
    smtp_username: str = Form(...),
    smtp_password: str = Form(None),
    smtp_security: str = Form(SmtpSecurity.STARTTLS),
    current_user: User = Depends(require_auth_user),
    db: Session = Depends(get_db)
):
    email_service = EmailService(db)
    success, msg, account = email_service.save_smtp_settings(
        user_id=current_user.id,
        sender_name=sender_name,
        email=email,
        smtp_host=smtp_host,
        smtp_port=smtp_port,
        smtp_username=smtp_username,
        smtp_password=smtp_password,
        smtp_security=smtp_security
    )

    if not success:
        return templates.TemplateResponse(
            request=request,
            name="settings/smtp.html",
            context={
                "user": current_user,
                "account": {
                    "sender_name": sender_name,
                    "email": email,
                    "smtp_host": smtp_host,
                    "smtp_port": smtp_port,
                    "smtp_username": smtp_username,
                    "smtp_security": smtp_security
                },
                "error": msg,
                "active_menu": "settings_email"
            },
            status_code=status.HTTP_400_BAD_REQUEST
        )

    return RedirectResponse(url="/settings/email?msg=saved", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/settings/email/test")
def test_smtp_settings(
    current_user: User = Depends(require_auth_user),
    db: Session = Depends(get_db)
):
    email_service = EmailService(db)
    test_res = email_service.test_connection(current_user.id)
    success_flag = "1" if test_res.success else "0"
    return RedirectResponse(
        url=f"/settings/email?test_success={success_flag}&test_result={test_res.message}",
        status_code=status.HTTP_303_SEE_OTHER
    )


@router.get("/profile", response_class=HTMLResponse)
def profile_view(
    request: Request,
    current_user: User = Depends(require_auth_user)
):
    return templates.TemplateResponse(
        request=request,
        name="settings/profile.html",
        context={
            "user": current_user,
            "error": None,
            "active_menu": "profile"
        }
    )


@router.post("/profile/password", response_class=HTMLResponse)
def change_password(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    current_user: User = Depends(require_auth_user),
    db: Session = Depends(get_db)
):
    if new_password != confirm_password:
        return templates.TemplateResponse(
            request=request,
            name="settings/profile.html",
            context={
                "user": current_user,
                "error": "A confirmação de senha não confere com a nova senha.",
                "active_menu": "profile"
            },
            status_code=status.HTTP_400_BAD_REQUEST
        )

    auth_service = AuthService(db)
    success, msg = auth_service.change_password(current_user.id, current_password, new_password)

    if not success:
        return templates.TemplateResponse(
            request=request,
            name="settings/profile.html",
            context={
                "user": current_user,
                "error": msg,
                "active_menu": "profile"
            },
            status_code=status.HTTP_400_BAD_REQUEST
        )

    return RedirectResponse(url="/profile?msg=pwd_changed", status_code=status.HTTP_303_SEE_OTHER)
