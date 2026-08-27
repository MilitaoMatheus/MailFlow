from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Enum
from sqlalchemy.orm import relationship
from app.database import Base


class UserStatus:
    ATIVO = "ATIVO"
    INATIVO = "INATIVO"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(150), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    status = Column(String(20), default=UserStatus.ATIVO, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relacionamentos com isolamento estrito por usuário
    email_accounts = relationship("EmailAccount", back_populates="user", cascade="all, delete-orphan")
    contacts = relationship("Contact", back_populates="user", cascade="all, delete-orphan")
    templates = relationship("Template", back_populates="user", cascade="all, delete-orphan")
    campaigns = relationship("Campaign", back_populates="user", cascade="all, delete-orphan")
    activity_logs = relationship("ActivityLog", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User id={self.id} email={self.email}>"
