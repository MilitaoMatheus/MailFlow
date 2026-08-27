from fastapi import APIRouter, Request, Depends, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.models.user import User
from app.controllers.deps import require_auth_user
from app.services.template_service import TemplateService

router = APIRouter(prefix="/templates", tags=["Templates"])
templates = Jinja2Templates(directory=str(settings.TEMPLATES_DIR))


@router.get("", response_class=HTMLResponse)
def list_templates(
    request: Request,
    current_user: User = Depends(require_auth_user),
    db: Session = Depends(get_db)
):
    template_service = TemplateService(db)
    user_templates = template_service.list_templates(current_user.id)

    return templates.TemplateResponse(
        request=request,
        name="templates/index.html",
        context={
            "user": current_user,
            "templates": user_templates,
            "active_menu": "templates"
        }
    )


@router.get("/new", response_class=HTMLResponse)
def new_template_form(
    request: Request,
    current_user: User = Depends(require_auth_user)
):
    default_header = '<h1 style="margin: 0; font-size: 24px; color: #ffffff;">{{empresa}}</h1>\n<p style="margin: 4px 0 0 0; font-size: 13px; color: #cbd5e1;">Novidades e Comunicações</p>'
    default_body = '<h2>Olá, {{nome}}!</h2>\n<p>Temos o prazer de compartilhar nossas últimas novidades e ofertas exclusivas com você.</p>\n<p style="text-align: center; margin: 30px 0;">\n  <a href="#" class="btn">Acessar Nossa Plataforma</a>\n</p>\n<p>Qualquer dúvida, nossa equipe está à total disposição.</p>\n<p>Atenciosamente,<br><strong>{{nome_perfil}}</strong></p>'
    default_footer = '<p style="margin: 0;">{{empresa}} &copy; {{data}} - Todos os direitos reservados.</p>\n<p style="margin: 5px 0 0 0;">Você está recebendo esta mensagem porque se cadastrou em nossa lista de novidades.</p>\n<p style="margin: 8px 0 0 0;"><a href="{{link_descadastro}}" style="color: #6366f1;">Cancelar inscrição</a></p>'

    return templates.TemplateResponse(
        request=request,
        name="templates/form.html",
        context={
            "user": current_user,
            "template": {
                "name": "",
                "header": default_header,
                "body": default_body,
                "footer": default_footer
            },
            "error": None,
            "active_menu": "templates"
        }
    )


@router.post("/new", response_class=HTMLResponse)
def create_template(
    request: Request,
    name: str = Form(...),
    header: str = Form(""),
    body: str = Form(...),
    footer: str = Form(""),
    current_user: User = Depends(require_auth_user),
    db: Session = Depends(get_db)
):
    template_service = TemplateService(db)
    success, msg, template = template_service.create_template(
        user_id=current_user.id,
        name=name,
        header=header,
        body=body,
        footer=footer
    )

    if not success:
        return templates.TemplateResponse(
            request=request,
            name="templates/form.html",
            context={
                "user": current_user,
                "template": {"name": name, "header": header, "body": body, "footer": footer},
                "error": msg,
                "active_menu": "templates"
            },
            status_code=status.HTTP_400_BAD_REQUEST
        )

    return RedirectResponse(url="/templates?msg=created", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/{template_id}/edit", response_class=HTMLResponse)
def edit_template_form(
    request: Request,
    template_id: int,
    current_user: User = Depends(require_auth_user),
    db: Session = Depends(get_db)
):
    template_service = TemplateService(db)
    template = template_service.get_template(current_user.id, template_id)
    if not template:
        return RedirectResponse(url="/templates", status_code=status.HTTP_303_SEE_OTHER)

    return templates.TemplateResponse(
        request=request,
        name="templates/form.html",
        context={
            "user": current_user,
            "template": template,
            "error": None,
            "active_menu": "templates"
        }
    )


@router.post("/{template_id}/edit", response_class=HTMLResponse)
def update_template(
    request: Request,
    template_id: int,
    name: str = Form(...),
    header: str = Form(""),
    body: str = Form(...),
    footer: str = Form(""),
    current_user: User = Depends(require_auth_user),
    db: Session = Depends(get_db)
):
    template_service = TemplateService(db)
    success, msg, template = template_service.update_template(
        user_id=current_user.id,
        template_id=template_id,
        name=name,
        header=header,
        body=body,
        footer=footer
    )

    if not success:
        return templates.TemplateResponse(
            request=request,
            name="templates/form.html",
            context={
                "user": current_user,
                "template": {"id": template_id, "name": name, "header": header, "body": body, "footer": footer},
                "error": msg,
                "active_menu": "templates"
            },
            status_code=status.HTTP_400_BAD_REQUEST
        )

    return RedirectResponse(url="/templates?msg=updated", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/{template_id}/delete")
def delete_template(
    template_id: int,
    current_user: User = Depends(require_auth_user),
    db: Session = Depends(get_db)
):
    template_service = TemplateService(db)
    template_service.delete_template(current_user.id, template_id)
    return RedirectResponse(url="/templates?msg=deleted", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/{template_id}/preview", response_class=HTMLResponse)
def preview_template_raw(
    template_id: int,
    current_user: User = Depends(require_auth_user),
    db: Session = Depends(get_db)
):
    template_service = TemplateService(db)
    template = template_service.get_template(current_user.id, template_id)
    if not template:
        return HTMLResponse("<h3>Template não encontrado</h3>", status_code=404)

    html_content = template_service.preview_template(template, current_user)
    return HTMLResponse(content=html_content)
