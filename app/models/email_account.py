from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class SmtpSecurity:
    SSL = "SSL"
    TLS = "TLS"
    STARTTLS = "STARTTLS"
    NONE = "NONE"


class EmailAccount(Base):
    __tablename__ = "email_accounts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    sender_name = Column(String(150), nullable=False)
    email = Column(String(255), nullable=False)
    smtp_host = Column(String(255), nullable=False)
    smtp_port = Column(Integer, nullable=False, default=587)
    smtp_username = Column(String(255), nullable=False)
    smtp_password_encrypted = Column(String(512), nullable=False)  # Armazenado criptografado via AES/Fernet
    smtp_security = Column(String(20), default=SmtpSecurity.STARTTLS, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    user = relationship("User", back_populates="email_accounts")

    def __repr__(self):
        return f"<EmailAccount id={self.id} user_id={self.user_id} email={self.email}>"
