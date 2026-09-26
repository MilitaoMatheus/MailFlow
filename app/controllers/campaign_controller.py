from typing import List
from fastapi import APIRouter, Request, Depends, Form, status, File, UploadFile, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db, SessionLocal
from app.models.user import User
from app.models.campaign import CampaignStatus
from app.controllers.deps import require_auth_user
from app.services.campaign_service import CampaignService
from app.services.template_service import TemplateService
from app.services.contact_service import ContactService
from app.services.email_service import EmailService
from app.services.security_service import SecurityService

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
async def create_campaign(
    request: Request,
    name: str = Form(...),
    subject: str = Form(...),
    template_id: int = Form(...),
    recipient_type: str = Form("all"),
    selected_contacts: List[int] = Form(None),
    files: List[UploadFile] = File(None),
    current_user: User = Depends(require_auth_user),
    db: Session = Depends(get_db)
):
    import os
    import shutil
    import uuid

    campaign_service = CampaignService(db)
    contact_ids = None if recipient_type == "all" else selected_contacts

    # Processamento e validação dos anexos
    attachments_meta = []
    allowed_extensions = {".pdf", ".doc", ".docx", ".png", ".jpg", ".jpeg", ".txt"}
    max_file_size = 5 * 1024 * 1024  # 5MB

    if files:
        for f in files:
            # Pular arquivos vazios (ocorre em envios sem arquivo no formulário HTML)
            if not f.filename:
                continue

            # Validar extensão
            _, ext = os.path.splitext(f.filename.lower())
            if ext not in allowed_extensions:
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
                        "error": f"Extensão do arquivo '{f.filename}' não permitida. Use apenas PDF, Word ou Imagens.",
                        "active_menu": "campaigns"
                    },
                    status_code=status.HTTP_400_BAD_REQUEST
                )

            # Criar pasta física 'uploads' no diretório raiz do projeto com isolamento por usuário
            upload_dir = settings.BASE_DIR / "uploads" / f"campaign_user_{current_user.id}"
            upload_dir.mkdir(parents=True, exist_ok=True)

            # Sanitizar nome para evitar Path Traversal e caracteres maliciosos
            safe_name = SecurityService.sanitize_filename(f.filename)
            unique_filename = f"{uuid.uuid4().hex}_{safe_name}"
            dest_path = (upload_dir / unique_filename).resolve()

            # Garantir que o caminho resolvido permanece estritamente dentro da pasta de upload
            if not str(dest_path).startswith(str(upload_dir.resolve())):
                continue

            # Ler conteúdo para verificar tamanho
            content = await f.read()
            if len(content) > max_file_size:
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
                        "error": f"O arquivo '{f.filename}' excede o tamanho limite de 5MB.",
                        "active_menu": "campaigns"
                    },
                    status_code=status.HTTP_400_BAD_REQUEST
                )

            with open(dest_path, "wb") as buffer:
                buffer.write(content)

            attachments_meta.append({
                "file_path": str(dest_path),
                "file_name": safe_name,
                "content_type": f.content_type or "application/octet-stream"
            })

    success, msg, campaign = campaign_service.create_campaign(
        user_id=current_user.id,
        name=name,
        subject=subject,
        template_id=template_id,
        contact_ids=contact_ids,
        attachments_meta=attachments_meta
    )

    if not success or not campaign:
        # Remover arquivos salvos em caso de falha de validação da campanha
        for att in attachments_meta:
            if os.path.exists(att["file_path"]):
                os.remove(att["file_path"])

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

    test_success = request.query_params.get("test_success")
    test_error = request.query_params.get("test_error")

    return templates.TemplateResponse(
        request=request,
        name="campaigns/show.html",
        context={
            "user": current_user,
            "report": report_data,
            "smtp_account": smtp_account,
            "test_success": test_success,
            "test_error": test_error,
            "active_menu": "campaigns"
        }
    )


def _bg_send_campaign(campaign_id: int, user_id: int, base_url: str):
    """Executa o envio da campanha em background com uma nova sessão de banco."""
    db_bg = SessionLocal()
    try:
        user_bg = db_bg.query(User).filter(User.id == user_id).first()
        if user_bg:
            service = CampaignService(db_bg)
            service.send_campaign(user_id=user_id, campaign_id=campaign_id, user=user_bg, base_url=base_url)
    finally:
        db_bg.close()


@router.post("/{campaign_id}/test-send", response_class=HTMLResponse)
def execute_test_send(
    request: Request,
    campaign_id: int,
    test_email: str = Form(...),
    current_user: User = Depends(require_auth_user),
    db: Session = Depends(get_db)
):
    import urllib.parse
    campaign_service = CampaignService(db)
    base_url = str(request.base_url).rstrip("/")
    success, msg = campaign_service.send_test_email(
        user_id=current_user.id,
        campaign_id=campaign_id,
        test_email=test_email,
        user=current_user,
        base_url=base_url
    )

    param = "test_success" if success else "test_error"
    return RedirectResponse(
        url=f"/campaigns/{campaign_id}?{param}={urllib.parse.quote(msg)}",
        status_code=status.HTTP_303_SEE_OTHER
    )


@router.post("/{campaign_id}/send", response_class=HTMLResponse)
def execute_campaign_send(
    request: Request,
    campaign_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_auth_user),
    db: Session = Depends(get_db)
):
    campaign_service = CampaignService(db)
    campaign = campaign_service.get_campaign(current_user.id, campaign_id)
    if not campaign:
        return RedirectResponse(url="/campaigns", status_code=status.HTTP_303_SEE_OTHER)

    if campaign.status == CampaignStatus.PROCESSANDO:
        return RedirectResponse(url=f"/campaigns/{campaign_id}?send_result=Esta campanha já está em processamento.", status_code=status.HTTP_303_SEE_OTHER)

    # Marca imediatamente como PROCESSANDO no banco
    campaign.status = CampaignStatus.PROCESSANDO
    db.commit()

    base_url = str(request.base_url).rstrip("/")
    background_tasks.add_task(_bg_send_campaign, campaign_id, current_user.id, base_url)

    return RedirectResponse(url=f"/campaigns/{campaign_id}?send_started=1", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/{campaign_id}/status")
def get_campaign_status(
    campaign_id: int,
    current_user: User = Depends(require_auth_user),
    db: Session = Depends(get_db)
):
    """Retorna dados de progresso em tempo real da campanha para polling."""
    campaign_service = CampaignService(db)
    campaign = campaign_service.get_campaign(current_user.id, campaign_id)
    if not campaign:
        return {"error": "Campanha não encontrada", "status": "NOT_FOUND"}

    total = campaign.total_recipients or 0
    processed = (campaign.total_sent or 0) + (campaign.total_failed or 0) + (campaign.total_invalid or 0) + (campaign.total_ignored or 0)
    pct = round((processed / total) * 100, 1) if total > 0 else (100.0 if campaign.status == CampaignStatus.CONCLUIDO else 0.0)

    return {
        "id": campaign.id,
        "name": campaign.name,
        "status": campaign.status,
        "total": total,
        "sent": campaign.total_sent or 0,
        "failed": campaign.total_failed or 0,
        "invalid": campaign.total_invalid or 0,
        "ignored": campaign.total_ignored or 0,
        "processed": processed,
        "progress_pct": min(100.0, pct),
        "is_finished": campaign.status in (CampaignStatus.CONCLUIDO, CampaignStatus.FALHA)
    }


@router.post("/{campaign_id}/delete")
def delete_campaign(
    campaign_id: int,
    current_user: User = Depends(require_auth_user),
    db: Session = Depends(get_db)
):
    campaign_service = CampaignService(db)
    success, msg = campaign_service.delete_campaign(current_user.id, campaign_id)
    return RedirectResponse(url=f"/campaigns?msg={msg}", status_code=status.HTTP_303_SEE_OTHER)


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
