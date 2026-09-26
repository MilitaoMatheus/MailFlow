from datetime import datetime, timezone
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.services.contact_service import ContactService
from app.models.campaign import Campaign, CampaignContact

router = APIRouter(tags=["Público"])
templates = Jinja2Templates(directory=str(settings.TEMPLATES_DIR))

# Binário de uma imagem PNG 1x1 pixel totalmente transparente (43 bytes)
TRANSPARENT_PNG_1X1 = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4"
    b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


@router.get("/track/open/{open_token}.png")
def track_email_open(open_token: str, db: Session = Depends(get_db)):
    """
    Endpoint público de rastreamento de abertura (Open Tracking).
    Chamado pelo cliente de e-mail ao carregar a imagem 1x1.
    Retorna o PNG transparente e registra a data/hora e contador de aberturas.
    """
    if open_token:
        recipient = db.query(CampaignContact).filter(CampaignContact.open_token == open_token).first()
        if recipient:
            now = datetime.now(timezone.utc)
            # Se for a primeira abertura registrada deste contato
            if recipient.opened_at is None:
                recipient.opened_at = now
                campaign = db.query(Campaign).filter(Campaign.id == recipient.campaign_id).first()
                if campaign:
                    campaign.total_opened = (campaign.total_opened or 0) + 1
            recipient.open_count = (recipient.open_count or 0) + 1
            db.commit()

    return Response(
        content=TRANSPARENT_PNG_1X1,
        media_type="image/png",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0, private",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )


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
