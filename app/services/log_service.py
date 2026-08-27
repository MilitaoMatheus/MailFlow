from typing import List
from sqlalchemy.orm import Session
from app.models.activity_log import ActivityLog
from app.repositories.log_repository import LogRepository


class LogService:
    """Serviço para consulta de logs de auditoria."""

    def __init__(self, db: Session):
        self.db = db
        self.log_repo = LogRepository(db)

    def list_recent_logs(self, user_id: int, limit: int = 15) -> List[ActivityLog]:
        return self.log_repo.list_logs(user_id=user_id, limit=limit)
