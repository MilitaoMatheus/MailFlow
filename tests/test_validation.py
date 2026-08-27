import pytest
from app.services.security_service import SecurityService
from app.services.contact_service import ContactService
from app.models.contact import ContactStatus


def test_email_syntax_validation():
    """Testa validações sintáticas conforme requisitos 5.1 e 28."""
    # Válidos
    valid_emails = [
        "joao@email.com",
        "joao.silva@gmail.com",
        "maria_santos@empresa.com.br",
        "contato+marketing@startup.io",
        "admin123@domain.co"
    ]
    for email in valid_emails:
        is_valid, clean = SecurityService.validate_email_syntax(email)
        assert is_valid is True, f"Deveria ser válido: {email}"
        assert clean == email.lower().strip()

    # Inválidos
    invalid_emails = [
        "joao@",
        "joao.com",
        "@email.com",
        "joao@.com",
        "joao@com.",
        "joao..silva@email.com",
        "espaço no email@email.com",
        "",
        None
    ]
    for email in invalid_emails:
        is_valid, err = SecurityService.validate_email_syntax(email)
        assert is_valid is False, f"Deveria ser inválido: {email}"


def test_contact_status_lifecycle(db_session, user_a):
    """Testa criação e transições de status de contatos."""
    contact_service = ContactService(db_session)

    # 1. Cadastro de contato válido -> status ATIVO
    ok, msg, c1 = contact_service.create_contact(
        user_id=user_a.id,
        name="Carlos Silva",
        email="carlos@empresa.com"
    )
    assert ok is True
    assert c1.status == ContactStatus.ATIVO
    assert len(c1.unsubscribe_token) > 10

    # 2. Cadastro com e-mail duplicado deve falhar
    ok_dup, msg_dup, _ = contact_service.create_contact(
        user_id=user_a.id,
        name="Carlos Duplicado",
        email="carlos@empresa.com"
    )
    assert ok_dup is False
    assert "já está cadastrado" in msg_dup

    # 3. Alternar status (toggle)
    ok_t, _, c_toggled = contact_service.toggle_status(user_a.id, c1.id)
    assert ok_t is True
    assert c_toggled.status == ContactStatus.INATIVO

    # 4. Alternar de volta
    ok_t2, _, c_toggled2 = contact_service.toggle_status(user_a.id, c1.id)
    assert ok_t2 is True
    assert c_toggled2.status == ContactStatus.ATIVO
