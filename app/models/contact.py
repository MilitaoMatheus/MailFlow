import secrets
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base


class ContactStatus:
    ATIVO = "ATIVO"
    INATIVO = "INATIVO"
    INVALIDO = "INVALIDO"
    DESCADASTRADO = "DESCADASTRADO"


def generate_unsubscribe_token():
    return secrets.token_urlsafe(32)


class Contact(Base):
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    name = Column(String(150), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    company = Column(String(150), nullable=True)
    phone = Column(String(50), nullable=True)
    status = Column(String(20), default=ContactStatus.ATIVO, nullable=False, index=True)
    unsubscribe_token = Column(String(64), unique=True, index=True, default=generate_unsubscribe_token, nullable=False)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Cada usuário tem sua lista de contatos isolada; e-mail deve ser único por usuário
    __table_args__ = (
        UniqueConstraint("user_id", "email", name="uq_user_contact_email"),
    )

    user = relationship("User", back_populates="contacts")
    campaign_contacts = relationship("CampaignContact", back_populates="contact")

    def __repr__(self):
        return f"<Contact id={self.id} user_id={self.user_id} email={self.email} status={self.status}>"
