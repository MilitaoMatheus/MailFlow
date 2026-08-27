from typing import List
from fastapi import APIRouter, Request, Depends, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.models.user import User
from app.controllers.deps import require_auth_user
from app.services.campaign_service import CampaignService
from app.services.template_service import TemplateService
from app.services.contact_service import ContactService
from app.services.email_service import EmailService

router = APIRouter(prefix="/campaigns", tags=["Campanhas"])
templates = Jinja2Templates(directory=str(settings.TEMPLATES_DIR))


@router.get("", response_class=HTMLResponse)
def list_campaigns(
    request: Request,
    page: int = 1,
    current_user: User = Depends(require_auth_user),
    db: Session = Depends(get_db)
):
    campaign_service = CampaignService(db)
    result = campaign_service.list_campaigns(user_id=current_user.id, page=page)

    return templates.TemplateResponse(
        request=request,
        name="campaigns/index.html",
        context={
            "user": current_user,
            "campaigns": result["campaigns"],
            "total_count": result["total_count"],
            "current_page": result["current_page"],
            "total_pages": result["total_pages"],
            "active_menu": "campaigns"
        }
    )


@router.get("/new", response_class=HTMLResponse)
def new_campaign_form(
    request: Request,
    current_user: User = Depends(require_auth_user),
    db: Session = Depends(get_db)
):
    template_service = TemplateService(db)
    contact_service = ContactService(db)
    email_service = EmailService(db)

    user_templates = template_service.list_templates(current_user.id)
    contacts = contact_service.contact_repo.get_all_active_contacts(current_user.id)
    smtp_account = email_service.get_smtp_account(current_user.id)

    return templates.TemplateResponse(
        request=request,
        name="campaigns/form.html",
        context={
            "user": current_user,
            "templates": user_templates,
            "contacts": contacts,
            "smtp_account": smtp_account,
            "error": None,
            "active_menu": "campaigns"
        }
    )


@router.post("/new", response_class=HTMLResponse)
def create_campaign(
    request: Request,
    name: str = Form(...),
    subject: str = Form(...),
    template_id: int = Form(...),
    recipient_type: str = Form("all"),
    selected_contacts: List[int] = Form(None),
    current_user: User = Depends(require_auth_user),
    db: Session = Depends(get_db)
):
    campaign_service = CampaignService(db)
    contact_ids = None if recipient_type == "all" else selected_contacts

    success, msg, campaign = campaign_service.create_campaign(
        user_id=current_user.id,
        name=name,
        subject=subject,
        template_id=template_id,
        contact_ids=contact_ids
    )

    if not success or not campaign:
        template_service = TemplateService(db)
        contact_service = ContactService(db)
        email_service = EmailService(db)
        return templates.TemplateResponse(
            request=request,
            name="campaigns/form.html",
            context={
                "user": current_user,
                "templates": template_service.list_templates(current_user.id),
                "contacts": contact_service.contact_repo.get_all_active_contacts(current_user.id),
                "smtp_account": email_service.get_smtp_account(current_user.id),
                "error": msg,
                "active_menu": "campaigns"
            },
            status_code=status.HTTP_400_BAD_REQUEST
        )

    return RedirectResponse(url=f"/campaigns/{campaign.id}", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/{campaign_id}", response_class=HTMLResponse)
def view_campaign_report(
    request: Request,
    campaign_id: int,
    current_user: User = Depends(require_auth_user),
    db: Session = Depends(get_db)
):
    campaign_service = CampaignService(db)
    email_service = EmailService(db)

    report_data = campaign_service.get_campaign_report(current_user.id, campaign_id)
    if not report_data:
        return RedirectResponse(url="/campaigns", status_code=status.HTTP_303_SEE_OTHER)

    smtp_account = email_service.get_smtp_account(current_user.id)

    return templates.TemplateResponse(
        request=request,
        name="campaigns/show.html",
        context={
            "user": current_user,
            "report": report_data,
            "smtp_account": smtp_account,
            "active_menu": "campaigns"
        }
    )


@router.post("/{campaign_id}/send", response_class=HTMLResponse)
def execute_campaign_send(
    request: Request,
    campaign_id: int,
    current_user: User = Depends(require_auth_user),
    db: Session = Depends(get_db)
):
    campaign_service = CampaignService(db)
    success, msg, report = campaign_service.send_campaign(
        user_id=current_user.id,
        campaign_id=campaign_id,
        user=current_user,
        base_url=str(request.base_url).rstrip("/")
    )

    return RedirectResponse(url=f"/campaigns/{campaign_id}?send_result={msg}", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/{campaign_id}/preview", response_class=HTMLResponse)
def preview_campaign_email(
    campaign_id: int,
    current_user: User = Depends(require_auth_user),
    db: Session = Depends(get_db)
):
    campaign_service = CampaignService(db)
    template_service = TemplateService(db)

    campaign = campaign_service.get_campaign(current_user.id, campaign_id)
    if not campaign or not campaign.template_id:
        return HTMLResponse("<h3>Prévia indisponível</h3>", status_code=404)

    template = template_service.get_template(current_user.id, campaign.template_id)
    if not template:
        return HTMLResponse("<h3>Template não encontrado</h3>", status_code=404)

    html_content = template_service.preview_template(template, current_user)
    return HTMLResponse(content=html_content)
