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
    """Inicializa as tabelas no banco de dados e aplica migrações leves."""
    # Importar todos os modelos para que o Base reconheça as tabelas
    import app.models  # noqa: F401
    Base.metadata.create_all(bind=engine)

    # Migrações leves para garantir colunas novas em bancos existentes
    try:
        from sqlalchemy import text
        import secrets
        with engine.connect() as conn:
            if settings.DATABASE_URL.startswith("sqlite"):
                # 1. Verifica colunas da tabela users
                cols_users = [c[1] for c in conn.execute(text("PRAGMA table_info(users)")).fetchall()]
                if "token_version" not in cols_users and len(cols_users) > 0:
                    conn.execute(text("ALTER TABLE users ADD COLUMN token_version INTEGER DEFAULT 1 NOT NULL"))
                    conn.commit()

                # 2. Verifica colunas da tabela campaigns
                cols_camp = [c[1] for c in conn.execute(text("PRAGMA table_info(campaigns)")).fetchall()]
                if "total_opened" not in cols_camp and len(cols_camp) > 0:
                    conn.execute(text("ALTER TABLE campaigns ADD COLUMN total_opened INTEGER DEFAULT 0 NOT NULL"))
                    conn.commit()

                # 3. Verifica colunas da tabela campaign_contacts
                cols_cc = [c[1] for c in conn.execute(text("PRAGMA table_info(campaign_contacts)")).fetchall()]
                if "open_token" not in cols_cc and len(cols_cc) > 0:
                    conn.execute(text("ALTER TABLE campaign_contacts ADD COLUMN open_token VARCHAR(64)"))
                    conn.commit()
                    # Gerar tokens únicos para registros existentes
                    rows = conn.execute(text("SELECT id FROM campaign_contacts WHERE open_token IS NULL")).fetchall()
                    for r in rows:
                        tok = secrets.token_urlsafe(32)
                        conn.execute(text("UPDATE campaign_contacts SET open_token = :tok WHERE id = :cid"), {"tok": tok, "cid": r[0]})
                    conn.commit()
                    conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_campaign_contacts_open_token ON campaign_contacts (open_token)"))
                    conn.commit()

                if "opened_at" not in cols_cc and len(cols_cc) > 0:
                    conn.execute(text("ALTER TABLE campaign_contacts ADD COLUMN opened_at DATETIME"))
                    conn.commit()

                if "open_count" not in cols_cc and len(cols_cc) > 0:
                    conn.execute(text("ALTER TABLE campaign_contacts ADD COLUMN open_count INTEGER DEFAULT 0 NOT NULL"))
                    conn.commit()
    except Exception:
        pass
