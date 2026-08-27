from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class CampaignStatus:
    RASCUNHO = "RASCUNHO"
    PROCESSANDO = "PROCESSANDO"
    CONCLUIDO = "CONCLUIDO"
    FALHA = "FALHA"


class CampaignContactStatus:
    PENDENTE = "PENDENTE"
    ENVIADO = "ENVIADO"
    FALHA = "FALHA"
    INVALIDO = "INVALIDO"
    IGNORADO = "IGNORADO"


class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    template_id = Column(Integer, ForeignKey("templates.id", ondelete="SET NULL"), nullable=True, index=True)
    
    name = Column(String(150), nullable=False)
    subject = Column(String(255), nullable=False)
    status = Column(String(20), default=CampaignStatus.RASCUNHO, nullable=False, index=True)
    
    total_recipients = Column(Integer, default=0, nullable=False)
    total_sent = Column(Integer, default=0, nullable=False)
    total_failed = Column(Integer, default=0, nullable=False)
    total_invalid = Column(Integer, default=0, nullable=False)
    total_ignored = Column(Integer, default=0, nullable=False)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    sent_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="campaigns")
    template = relationship("Template", back_populates="campaigns")
    recipients = relationship("CampaignContact", back_populates="campaign", cascade="all, delete-orphan")
    attachments = relationship("CampaignAttachment", back_populates="campaign", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Campaign id={self.id} user_id={self.user_id} name={self.name} status={self.status}>"


class CampaignContact(Base):
    __tablename__ = "campaign_contacts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
    contact_id = Column(Integer, ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True, index=True)
    
    name = Column(String(150), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    status = Column(String(20), default=CampaignContactStatus.PENDENTE, nullable=False, index=True)
    error_message = Column(Text, nullable=True)
    sent_at = Column(DateTime, nullable=True)

    campaign = relationship("Campaign", back_populates="recipients")
    contact = relationship("Contact", back_populates="campaign_contacts")

    def __repr__(self):
        return f"<CampaignContact id={self.id} campaign_id={self.campaign_id} email={self.email} status={self.status}>"
