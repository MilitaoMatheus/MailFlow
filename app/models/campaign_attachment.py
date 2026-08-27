from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class CampaignAttachment(Base):
    __tablename__ = "campaign_attachments"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
    
    file_path = Column(String(512), nullable=False)   # Caminho local absoluto ou relativo no disco do servidor
    file_name = Column(String(255), nullable=False)   # Nome original do arquivo (ex: curriculo.pdf)
    content_type = Column(String(100), nullable=False) # Tipo MIME (ex: application/pdf)

    campaign = relationship("Campaign", back_populates="attachments")

    def __repr__(self):
        return f"<CampaignAttachment id={self.id} campaign_id={self.campaign_id} file_name={self.file_name}>"
