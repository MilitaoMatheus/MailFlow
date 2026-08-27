from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class Template(Base):
    __tablename__ = "templates"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    name = Column(String(150), nullable=False)
    header = Column(Text, nullable=False, default="")
    body = Column(Text, nullable=False, default="")
    footer = Column(Text, nullable=False, default="")
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    user = relationship("User", back_populates="templates")
    campaigns = relationship("Campaign", back_populates="template")

    def __repr__(self):
        return f"<Template id={self.id} user_id={self.user_id} name={self.name}>"
