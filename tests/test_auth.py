import pytest
from app.services.auth_service import AuthService
from app.services.security_service import SecurityService
from app.models.user import UserStatus


def test_auth_registration_and_login(db_session):
    """Testa cadastro e autenticação de usuário."""
    auth_service = AuthService(db_session)

    # 1. Cadastro com dados válidos
    ok, msg, user = auth_service.register(
        name="Teste Usuário",
        email="teste@dominio.com",
        password="minhasenhaforte"
    )
    assert ok is True
    assert user is not None
    assert user.email == "teste@dominio.com"
    assert user.status == UserStatus.ATIVO
    assert SecurityService.verify_password("minhasenhaforte", user.password_hash)

    # 2. Cadastro com mesmo e-mail deve falhar
    ok_dup, msg_dup, _ = auth_service.register(
        name="Outro Usuário",
        email="teste@dominio.com",
        password="outrasenha123"
    )
    assert ok_dup is False
    assert "já está cadastrado" in msg_dup

    # 3. Login com credenciais corretas
    ok_login, msg_login, logged_user = auth_service.authenticate(
        email="teste@dominio.com",
        password="minhasenhaforte"
    )
    assert ok_login is True
    assert logged_user.id == user.id

    # 4. Login com senha errada
    ok_wrong, msg_wrong, _ = auth_service.authenticate(
        email="teste@dominio.com",
        password="senhaerrada"
    )
    assert ok_wrong is False
    assert "incorretos" in msg_wrong

    # 5. Login com usuário inexistente
    ok_no, msg_no, _ = auth_service.authenticate(
        email="inexistente@dominio.com",
        password="qualquersenha"
    )
    assert ok_no is False


def test_session_token_tampering():
    """Testa geração e validação de tokens de sessão com detecção de violação."""
    token = AuthService.create_session_token(user_id=42)
    assert token is not None

    uid = AuthService.decode_session_token(token)
    assert uid == 42

    # Token corrompido / alterado
    tampered_token = token[:-4] + "fake"
    assert AuthService.decode_session_token(tampered_token) is None
    assert AuthService.decode_session_token("token.invalido.xyz") is None
