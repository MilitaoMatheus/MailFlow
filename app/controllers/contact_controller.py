from fastapi import APIRouter, Request, Depends, Form, UploadFile, File, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.models.user import User
from app.controllers.deps import require_auth_user
from app.services.contact_service import ContactService
from app.models.contact import ContactStatus

router = APIRouter(prefix="/contacts", tags=["Contatos"])
templates = Jinja2Templates(directory=str(settings.TEMPLATES_DIR))


@router.get("", response_class=HTMLResponse)
def list_contacts(
    request: Request,
    search: str = "",
    status_filter: str = "",
    page: int = 1,
    current_user: User = Depends(require_auth_user),
    db: Session = Depends(get_db)
):
    contact_service = ContactService(db)
    result = contact_service.list_contacts(
        user_id=current_user.id,
        search=search if search else None,
        status=status_filter if status_filter else None,
        page=page,
        page_size=20
    )

    return templates.TemplateResponse(
        request=request,
        name="contacts/index.html",
        context={
            "user": current_user,
            "contacts": result["contacts"],
            "total_count": result["total_count"],
            "current_page": result["current_page"],
            "total_pages": result["total_pages"],
            "search": search,
            "status_filter": status_filter,
            "active_menu": "contacts"
        }
    )


@router.get("/new", response_class=HTMLResponse)
def new_contact_form(
    request: Request,
    current_user: User = Depends(require_auth_user)
):
    return templates.TemplateResponse(
        request=request,
        name="contacts/form.html",
        context={
            "user": current_user,
            "contact": None,
            "error": None,
            "active_menu": "contacts"
        }
    )


@router.post("/new", response_class=HTMLResponse)
def create_contact(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    company: str = Form(None),
    phone: str = Form(None),
    contact_status: str = Form(ContactStatus.ATIVO),
    current_user: User = Depends(require_auth_user),
    db: Session = Depends(get_db)
):
    contact_service = ContactService(db)
    success, msg, contact = contact_service.create_contact(
        user_id=current_user.id,
        name=name,
        email=email,
        company=company,
        phone=phone,
        status=contact_status
    )

    if not success:
        return templates.TemplateResponse(
            request=request,
            name="contacts/form.html",
            context={
                "user": current_user,
                "contact": {"name": name, "email": email, "company": company, "phone": phone, "status": contact_status},
                "error": msg,
                "active_menu": "contacts"
            },
            status_code=status.HTTP_400_BAD_REQUEST
        )

    return RedirectResponse(url="/contacts?msg=created", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/{contact_id}/edit", response_class=HTMLResponse)
def edit_contact_form(
    request: Request,
    contact_id: int,
    current_user: User = Depends(require_auth_user),
    db: Session = Depends(get_db)
):
    contact_service = ContactService(db)
    contact = contact_service.get_contact(current_user.id, contact_id)
    if not contact:
        return RedirectResponse(url="/contacts", status_code=status.HTTP_303_SEE_OTHER)

    return templates.TemplateResponse(
        request=request,
        name="contacts/form.html",
        context={
            "user": current_user,
            "contact": contact,
            "error": None,
            "active_menu": "contacts"
        }
    )


@router.post("/{contact_id}/edit", response_class=HTMLResponse)
def update_contact(
    request: Request,
    contact_id: int,
    name: str = Form(...),
    email: str = Form(...),
    company: str = Form(None),
    phone: str = Form(None),
    contact_status: str = Form(ContactStatus.ATIVO),
    current_user: User = Depends(require_auth_user),
    db: Session = Depends(get_db)
):
    contact_service = ContactService(db)
    success, msg, contact = contact_service.update_contact(
        user_id=current_user.id,
        contact_id=contact_id,
        name=name,
        email=email,
        company=company,
        phone=phone,
        status=contact_status
    )

    if not success:
        return templates.TemplateResponse(
            request=request,
            name="contacts/form.html",
            context={
                "user": current_user,
                "contact": {"id": contact_id, "name": name, "email": email, "company": company, "phone": phone, "status": contact_status},
                "error": msg,
                "active_menu": "contacts"
            },
            status_code=status.HTTP_400_BAD_REQUEST
        )

    return RedirectResponse(url="/contacts?msg=updated", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/{contact_id}/delete")
def delete_contact(
    contact_id: int,
    current_user: User = Depends(require_auth_user),
    db: Session = Depends(get_db)
):
    contact_service = ContactService(db)
    contact_service.delete_contact(current_user.id, contact_id)
    return RedirectResponse(url="/contacts?msg=deleted", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/{contact_id}/toggle")
def toggle_contact_status(
    contact_id: int,
    current_user: User = Depends(require_auth_user),
    db: Session = Depends(get_db)
):
    contact_service = ContactService(db)
    contact_service.toggle_status(current_user.id, contact_id)
    return RedirectResponse(url="/contacts", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/import", response_class=HTMLResponse)
def import_page(
    request: Request,
    current_user: User = Depends(require_auth_user)
):
    return templates.TemplateResponse(
        request=request,
        name="contacts/import.html",
        context={
            "user": current_user,
            "result": None,
            "error": None,
            "active_menu": "contacts"
        }
    )


@router.post("/import", response_class=HTMLResponse)
async def import_csv_file(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(require_auth_user),
    db: Session = Depends(get_db)
):
    contact_service = ContactService(db)
    try:
        content_bytes = await file.read()
        csv_text = content_bytes.decode("utf-8-sig", errors="replace")
        result = contact_service.import_csv(current_user.id, csv_text)

        return templates.TemplateResponse(
            request=request,
            name="contacts/import.html",
            context={
                "user": current_user,
                "result": result,
                "error": None,
                "active_menu": "contacts"
            }
        )
    except Exception as e:
        return templates.TemplateResponse(
            request=request,
            name="contacts/import.html",
            context={
                "user": current_user,
                "result": None,
                "error": f"Erro ao ler arquivo: {str(e)}",
                "active_menu": "contacts"
            }
        )


@router.get("/export")
def export_contacts(
    current_user: User = Depends(require_auth_user),
    db: Session = Depends(get_db)
):
    contact_service = ContactService(db)
    csv_data = contact_service.export_csv(current_user.id)
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=contatos_{current_user.name.lower().replace(' ', '_')}.csv"}
    )
