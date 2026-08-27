import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.database import Base, get_db
from app.main import app
from app.models import User, Contact, Template, EmailAccount, ContactStatus
from app.services.security_service import SecurityService
from app.services.auth_service import AuthService
from app.providers.mock_provider import MockEmailProvider

# Banco em memória isolado para testes
TEST_DATABASE_URL = "sqlite:///:memory:"

engine_test = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)


@pytest.fixture(scope="function")
def db_session():
    """Cria as tabelas em um banco de dados em memória limpo para cada teste."""
    Base.metadata.create_all(bind=engine_test)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine_test)


@pytest.fixture(scope="function")
def client(db_session):
    """Cliente de teste com injeção do banco de dados em memória."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def user_a(db_session) -> User:
    """Perfil de teste A (João)."""
    user = User(
        name="João Silva",
        email="joao@empresa.com",
        password_hash=SecurityService.hash_password("senha123"),
        status="ATIVO"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # Configuração SMTP para João
    smtp = EmailAccount(
        user_id=user.id,
        sender_name="João Silva",
        email="joao@empresa.com",
        smtp_host="smtp.empresa.com",
        smtp_port=587,
        smtp_username="joao@empresa.com",
        smtp_password_encrypted=SecurityService.encrypt_smtp_password("app-pass-joao"),
        smtp_security="STARTTLS",
        is_active=True
    )
    db_session.add(smtp)
    db_session.commit()
    return user


@pytest.fixture
def user_b(db_session) -> User:
    """Perfil de teste B (Maria)."""
    user = User(
        name="Maria Souza",
        email="maria@empresa.com",
        password_hash=SecurityService.hash_password("senha456"),
        status="ATIVO"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # Configuração SMTP para Maria
    smtp = EmailAccount(
        user_id=user.id,
        sender_name="Maria Souza",
        email="maria@empresa.com",
        smtp_host="smtp.maria.com",
        smtp_port=465,
        smtp_username="maria@empresa.com",
        smtp_password_encrypted=SecurityService.encrypt_smtp_password("app-pass-maria"),
        smtp_security="SSL",
        is_active=True
    )
    db_session.add(smtp)
    db_session.commit()
    return user


@pytest.fixture
def client_user_a(client, user_a):
    """Cliente HTTP autenticado como Usuário A."""
    token = AuthService.create_session_token(user_a.id)
    client.cookies.set("session_token", token)
    return client


@pytest.fixture
def client_user_b(client, user_b):
    """Cliente HTTP autenticado como Usuário B."""
    token = AuthService.create_session_token(user_b.id)
    client.cookies.set("session_token", token)
    return client
