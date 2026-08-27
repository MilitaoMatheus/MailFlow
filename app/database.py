from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.config import settings

connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True
)

# Habilitar suporte a Foreign Keys no SQLite
if settings.DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dependency para obter sessão do banco de dados nas rotas/controllers."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Inicializa as tabelas no banco de dados."""
    # Importar todos os modelos para que o Base reconheça as tabelas
    import app.models  # noqa: F401
    Base.metadata.create_all(bind=engine)
