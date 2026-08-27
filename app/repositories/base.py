from sqlalchemy.orm import Session


class BaseRepository:
    """Classe base para repositórios com injeção de sessão do banco de dados."""

    def __init__(self, db: Session):
        self.db = db
