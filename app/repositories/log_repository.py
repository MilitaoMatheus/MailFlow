from typing import List, Optional
from sqlalchemy import desc
from app.repositories.base import BaseRepository
from app.models.activity_log import ActivityLog


class LogRepository(BaseRepository):

    def create_log(
        self,
        user_id: Optional[int],
        action: str,
        description: str,
        ip_address: Optional[str] = None
    ) -> ActivityLog:
        """Registra uma ação de auditoria segura (sem expor credenciais)."""
        log = ActivityLog(
            user_id=user_id,
            action=action.upper(),
            description=description.strip(),
            ip_address=ip_address
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log

    def list_logs(self, user_id: int, limit: int = 15) -> List[ActivityLog]:
        """Lista histórico recente de auditoria do perfil."""
        return self.db.query(ActivityLog).filter(
            ActivityLog.user_id == user_id
        ).order_by(desc(ActivityLog.created_at)).limit(limit).all()
