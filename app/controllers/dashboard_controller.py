from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.models.user import User
from app.controllers.deps import require_auth_user
from app.repositories.campaign_repository import CampaignRepository
from app.services.email_service import EmailService
from app.services.log_service import LogService

router = APIRouter(tags=["Dashboard"])
templates = Jinja2Templates(directory=str(settings.TEMPLATES_DIR))


@router.get("/", response_class=HTMLResponse)
def root_redirect():
    return RedirectResponse(url="/dashboard")


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard_view(
    request: Request,
    current_user: User = Depends(require_auth_user),
    db: Session = Depends(get_db)
):
    campaign_repo = CampaignRepository(db)
    email_service = EmailService(db)
    log_service = LogService(db)

    metrics = campaign_repo.get_dashboard_metrics(current_user.id)
    smtp_account = email_service.get_smtp_account(current_user.id)
    recent_logs = log_service.list_recent_logs(current_user.id, limit=8)

    return templates.TemplateResponse(
        request=request,
        name="dashboard/index.html",
        context={
            "user": current_user,
            "metrics": metrics,
            "smtp_account": smtp_account,
            "recent_logs": recent_logs,
            "active_menu": "dashboard"
        }
    )
