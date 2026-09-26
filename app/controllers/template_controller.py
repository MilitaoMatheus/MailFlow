import json
from fastapi import APIRouter, Request, Depends, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.models.user import User
from app.controllers.deps import require_auth_user
from app.services.template_service import TemplateService
from app.services.preset_templates import get_all_presets, compile_preset_html

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
    presets = get_all_presets()

    return templates.TemplateResponse(
        request=request,
        name="templates/index.html",
        context={
            "user": current_user,
            "templates": user_templates,
            "presets": presets,
            "active_menu": "templates"
        }
    )


@router.get("/new", response_class=HTMLResponse)
def new_template_form(
    request: Request,
    preset_id: str = "newsletter",
    current_user: User = Depends(require_auth_user)
):
    presets = get_all_presets()
    selected_preset = next((p for p in presets if p["id"] == preset_id), presets[0])
    
    default_header, default_body, default_footer = compile_preset_html(
        header_title=selected_preset["header_title"],
        header_subtitle=selected_preset["header_subtitle"],
        headline=selected_preset["headline"],
        greeting=selected_preset["greeting"],
        message=selected_preset["message"],
        btn_text=selected_preset["btn_text"],
        btn_url=selected_preset["btn_url"],
        footer_note=selected_preset["footer_note"],
        brand_color=selected_preset["brand_color"],
        header_style=selected_preset["header_style"]
    )

    template_dict = {
        "name": selected_preset["name"],
        "header": default_header,
        "body": default_body,
        "footer": default_footer
    }

    return templates.TemplateResponse(
        request=request,
        name="templates/form.html",
        context={
            "user": current_user,
            "presets": presets,
            "presets_json": json.dumps(presets),
            "selected_preset": selected_preset,
            "template": template_dict,
            "template_json": json.dumps(template_dict),
            "is_edit": False,
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
        presets = get_all_presets()
        template_dict = {"name": name, "header": header, "body": body, "footer": footer}
        return templates.TemplateResponse(
            request=request,
            name="templates/form.html",
            context={
                "user": current_user,
                "presets": presets,
                "presets_json": json.dumps(presets),
                "selected_preset": presets[0],
                "template": template_dict,
                "template_json": json.dumps(template_dict),
                "is_edit": False,
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

    presets = get_all_presets()
    template_dict = {
        "id": template.id,
        "name": template.name,
        "header": template.header or "",
        "body": template.body or "",
        "footer": template.footer or ""
    }

    return templates.TemplateResponse(
        request=request,
        name="templates/form.html",
        context={
            "user": current_user,
            "template": template,
            "template_json": json.dumps(template_dict),
            "is_edit": True,
            "presets": presets,
            "presets_json": json.dumps(presets),
            "selected_preset": presets[0],
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
        presets = get_all_presets()
        template_dict = {"id": template_id, "name": name, "header": header, "body": body, "footer": footer}
        return templates.TemplateResponse(
            request=request,
            name="templates/form.html",
            context={
                "user": current_user,
                "presets": presets,
                "presets_json": json.dumps(presets),
                "selected_preset": presets[0],
                "template": template_dict,
                "template_json": json.dumps(template_dict),
                "is_edit": True,
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
