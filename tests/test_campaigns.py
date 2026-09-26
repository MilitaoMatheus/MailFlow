import pytest
from app.services.contact_service import ContactService
from app.services.template_service import TemplateService
from app.services.campaign_service import CampaignService
from app.models.campaign import CampaignStatus, CampaignContactStatus
from app.models.contact import ContactStatus
from app.providers.mock_provider import MockEmailProvider


def test_campaign_batch_send_fault_tolerance(db_session, user_a, monkeypatch):
    """
    Testa fluxo completo de disparo por lote com tolerância a falhas:
    Destinatários válidos, destinatário com falha simulada e destinatário descadastrado.
    """
    contact_service = ContactService(db_session)
    template_service = TemplateService(db_session)
    campaign_service = CampaignService(db_session)

    # Configurar mock provider com domínio 'fail.com' que gera erro
    mock_provider = MockEmailProvider(
        sender_name="João Teste",
        sender_email="joao@empresa.com",
        fail_domains=["fail.com"]
    )
    monkeypatch.setattr(campaign_service.email_service, "get_provider", lambda uid: (mock_provider, None))

    # 1. Criar contatos
    _, _, c_valid = contact_service.create_contact(user_a.id, "Lucas Valido", "lucas@gmail.com")
    _, _, c_fail = contact_service.create_contact(user_a.id, "Marcos Erro", "marcos@fail.com")
    _, _, c_unsub = contact_service.create_contact(user_a.id, "Paula Optout", "paula@empresa.com")
    
    # Marcar Paula como DESCADASTRADA
    c_unsub.status = ContactStatus.DESCADASTRADO
    db_session.commit()

    # 2. Criar template
    _, _, template = template_service.create_template(
        user_id=user_a.id,
        name="Template de Teste de Campanha",
        header="<h3>Cabecalho</h3>",
        body="<p>Ola, {{nome}}!</p>",
        footer="<p>Rodape</p>"
    )

    # 3. Criar campanha incluindo todos os 3 contatos
    ok_c, msg_c, campaign = campaign_service.create_campaign(
        user_id=user_a.id,
        name="Campanha de Teste Lote",
        subject="Assunto Teste",
        template_id=template.id,
        contact_ids=[c_valid.id, c_fail.id, c_unsub.id]
    )
    assert ok_c is True
    assert campaign.total_recipients == 3

    # 4. Executar disparo
    ok_send, msg_send, report = campaign_service.send_campaign(
        user_id=user_a.id,
        campaign_id=campaign.id,
        user=user_a
    )
    assert ok_send is True
    assert report["total_sent"] == 1  # Apenas lucas@gmail.com
    assert report["total_failed"] == 1  # marcos@fail.com
    assert report["total_ignored"] == 1  # paula (descadastrada)
    assert campaign.status == CampaignStatus.CONCLUIDO

    # 5. Conferir relatório detalhado dos destinatários
    full_report = campaign_service.get_campaign_report(user_a.id, campaign.id)
    recipients = full_report["recipients"]
    
    status_by_email = {r.email: r.status for r in recipients}
    assert status_by_email["lucas@gmail.com"] == CampaignContactStatus.ENVIADO
    assert status_by_email["marcos@fail.com"] == CampaignContactStatus.FALHA
    assert status_by_email["paula@empresa.com"] == CampaignContactStatus.IGNORADO

    # Verificar que o e-mail de Lucas foi de fato registrado no MockProvider
    assert len(mock_provider.sent_emails) == 1
    assert mock_provider.sent_emails[0]["to_email"] == "lucas@gmail.com"
    assert "Ola, Lucas Valido!" in mock_provider.sent_emails[0]["html_content"]


def test_campaign_send_background_endpoint_flow(db_session, client, user_a, monkeypatch):
    """
    Testa o disparo real de campanha através do endpoint HTTP POST /campaigns/{id}/send,
    verificando que a tarefa em background é executada sem travar no status PROCESSANDO.
    """
    from app.services.auth_service import AuthService
    from app.services.email_service import EmailService
    from tests.conftest import TestingSessionLocal

    contact_service = ContactService(db_session)
    template_service = TemplateService(db_session)
    campaign_service = CampaignService(db_session)

    mock_provider = MockEmailProvider(sender_name=user_a.name, sender_email=user_a.email)
    monkeypatch.setattr(EmailService, "get_provider", lambda self, uid: (mock_provider, None))
    monkeypatch.setattr("app.controllers.campaign_controller.SessionLocal", TestingSessionLocal)

    # 1. Criar contato e template
    _, _, contact = contact_service.create_contact(user_a.id, "Destinatário Real", "real@empresa.com")
    _, _, template = template_service.create_template(
        user_id=user_a.id,
        name="Template Real",
        header="<h1>Topo</h1>",
        body="<p>Conteúdo Real para {{nome}}</p>",
        footer="<p>Rodapé</p>"
    )

    # 2. Criar campanha
    ok_c, _, campaign = campaign_service.create_campaign(
        user_id=user_a.id,
        name="Campanha Real Teste",
        subject="Assunto Real",
        template_id=template.id,
        contact_ids=[contact.id]
    )
    assert ok_c is True
    assert campaign.status == CampaignStatus.RASCUNHO

    # 3. Autenticar usuário
    session_token = AuthService.create_session_token(user_a.id, getattr(user_a, "token_version", 1))
    client.cookies.set("session_token", session_token)

    # 4. Chamar endpoint POST /campaigns/{id}/send
    response = client.post(f"/campaigns/{campaign.id}/send", follow_redirects=False)
    assert response.status_code == 303
    assert "send_started=1" in response.headers["location"]

    # 5. Conferir que o mock provider recebeu o e-mail real
    assert len(mock_provider.sent_emails) == 1
    assert mock_provider.sent_emails[0]["to_email"] == "real@empresa.com"
    assert "Conteúdo Real para Destinatário Real" in mock_provider.sent_emails[0]["html_content"]

    # 6. Conferir que a campanha foi concluída no banco e o destinatário marcado como ENVIADO
    db_session.refresh(campaign)
    assert campaign.status == CampaignStatus.CONCLUIDO
    assert campaign.total_sent == 1
    assert campaign.total_failed == 0

    recipients = campaign_service.campaign_repo.get_campaign_recipients(campaign.id)
    assert len(recipients) == 1
    assert recipients[0].status == CampaignContactStatus.ENVIADO

