from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy import desc, func
from app.repositories.base import BaseRepository
from app.models.campaign import Campaign, CampaignContact, CampaignStatus, CampaignContactStatus
from app.models.campaign_attachment import CampaignAttachment
from app.models.contact import Contact


class CampaignRepository(BaseRepository):

    def get_by_id(self, user_id: int, campaign_id: int) -> Optional[Campaign]:
        """Recupera campanha garantindo que pertence exclusivamente ao usuário informado."""
        return self.db.query(Campaign).filter(
            Campaign.id == campaign_id,
            Campaign.user_id == user_id
        ).first()

    def list_campaigns(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0
    ) -> List[Campaign]:
        """Lista histórico de campanhas do usuário."""
        return self.db.query(Campaign).filter(
            Campaign.user_id == user_id
        ).order_by(desc(Campaign.created_at)).offset(offset).limit(limit).all()

    def count_campaigns(self, user_id: int) -> int:
        return self.db.query(Campaign).filter(Campaign.user_id == user_id).count()

    def create(
        self,
        user_id: int,
        name: str,
        subject: str,
        template_id: Optional[int],
        contacts: List[Contact],
        attachments_meta: Optional[List[Dict[str, str]]] = None
    ) -> Campaign:
        """Cria campanha e associa a lista inicial de destinatários."""
        campaign = Campaign(
            user_id=user_id,
            template_id=template_id,
            name=name.strip(),
            subject=subject.strip(),
            status=CampaignStatus.RASCUNHO,
            total_recipients=len(contacts),
            total_sent=0,
            total_failed=0,
            total_invalid=0,
            total_ignored=0
        )
        self.db.add(campaign)
        self.db.flush()  # Obtém campaign.id

        # Criar os registros de destinatários
        for contact in contacts:
            cc = CampaignContact(
                campaign_id=campaign.id,
                contact_id=contact.id,
                name=contact.name,
                email=contact.email,
                status=CampaignContactStatus.PENDENTE
            )
            self.db.add(cc)

        # Criar os registros de anexos
        if attachments_meta:
            for att in attachments_meta:
                ca = CampaignAttachment(
                    campaign_id=campaign.id,
                    file_path=att["file_path"],
                    file_name=att["file_name"],
                    content_type=att["content_type"]
                )
                self.db.add(ca)

        self.db.commit()
        self.db.refresh(campaign)
        return campaign

    def update_campaign_progress(
        self,
        campaign_id: int,
        status: str,
        total_sent: int,
        total_failed: int,
        total_invalid: int,
        total_ignored: int,
        sent_at: Optional[datetime] = None
    ) -> None:
        """Atualiza contadores e status final da campanha."""
        campaign = self.db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if campaign:
            campaign.status = status
            campaign.total_sent = total_sent
            campaign.total_failed = total_failed
            campaign.total_invalid = total_invalid
            campaign.total_ignored = total_ignored
            if sent_at:
                campaign.sent_at = sent_at
            self.db.commit()

    def update_recipient_status(
        self,
        campaign_contact_id: int,
        status: str,
        error_message: Optional[str] = None,
        sent_at: Optional[datetime] = None
    ) -> None:
        """Atualiza o resultado individual do disparo para um destinatário."""
        cc = self.db.query(CampaignContact).filter(CampaignContact.id == campaign_contact_id).first()
        if cc:
            cc.status = status
            cc.error_message = error_message
            cc.sent_at = sent_at or datetime.now(timezone.utc)
            self.db.commit()

    def get_campaign_recipients(self, campaign_id: int) -> List[CampaignContact]:
        """Lista todos os destinatários e status de disparo de uma campanha."""
        return self.db.query(CampaignContact).filter(
            CampaignContact.campaign_id == campaign_id
        ).order_by(CampaignContact.id.asc()).all()

    def get_dashboard_metrics(self, user_id: int) -> Dict[str, Any]:
        """Calcula métricas agregadas do dashboard exclusivamente para o perfil."""
        total_campaigns = self.count_campaigns(user_id)
        total_contacts = self.db.query(Contact).filter(Contact.user_id == user_id).count()
        
        # Agregação de enviados e falhas
        agg = self.db.query(
            func.sum(Campaign.total_sent).label("sent"),
            func.sum(Campaign.total_failed).label("failed"),
            func.sum(Campaign.total_invalid).label("invalid")
        ).filter(Campaign.user_id == user_id).first()

        total_sent = agg.sent or 0 if agg else 0
        total_failed = agg.failed or 0 if agg else 0
        total_invalid = agg.invalid or 0 if agg else 0
        total_attempts = total_sent + total_failed + total_invalid

        success_rate = 0.0
        if total_attempts > 0:
            success_rate = round((total_sent / total_attempts) * 100, 1)

        recent_campaigns = self.list_campaigns(user_id, limit=5)

        return {
            "total_campaigns": total_campaigns,
            "total_contacts": total_contacts,
            "total_sent": total_sent,
            "total_failed": total_failed,
            "total_invalid": total_invalid,
            "success_rate": success_rate,
            "recent_campaigns": recent_campaigns
        }
