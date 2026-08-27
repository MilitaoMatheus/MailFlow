import pytest
from app.services.contact_service import ContactService
from app.models.contact import ContactStatus


def test_unsubscribe_workflow(db_session, user_a, client):
    """Testa o fluxo completo de descadastro (opt-out) por token."""
    contact_service = ContactService(db_session)

    # 1. Cadastra contato ativo
    ok, _, contact = contact_service.create_contact(
        user_id=user_a.id,
        name="Roberto Cliente",
        email="roberto@empresa.com"
    )
    assert ok is True
    assert contact.status == ContactStatus.ATIVO
    token = contact.unsubscribe_token
    assert token is not None

    # 2. Requisição HTTP pública para a rota de descadastro
    response = client.get(f"/unsubscribe?token={token}")
    assert response.status_code == 200
    assert "Descadastro Concluído" in response.text
    assert "roberto@empresa.com" in response.text

    # 3. Verificar que o status no banco foi atualizado para DESCADASTRADO
    db_session.refresh(contact)
    assert contact.status == ContactStatus.DESCADASTRADO

    # 4. Requisição com token inválido
    bad_resp = client.get("/unsubscribe?token=token-invalido-inexistente")
    assert bad_resp.status_code == 200
    assert "inválido" in bad_resp.text.lower()
