from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.services.contact_service import ContactService

router = APIRouter(tags=["Público"])
templates = Jinja2Templates(directory=str(settings.TEMPLATES_DIR))


@router.get("/unsubscribe", response_class=HTMLResponse)
def public_unsubscribe(
    request: Request,
    token: str = "",
    db: Session = Depends(get_db)
):
    contact_service = ContactService(db)
    success, msg, contact = contact_service.unsubscribe_by_token(token)

    return templates.TemplateResponse(
        request=request,
        name="public/unsubscribed.html",
        context={
            "success": success,
            "message": msg,
            "contact": contact
        }
    )
