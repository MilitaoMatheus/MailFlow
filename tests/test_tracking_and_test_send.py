import pytest
from app.services.contact_service import ContactService
from app.services.template_service import TemplateService
from app.services.campaign_service import CampaignService
from app.services.auth_service import AuthService
from app.models.campaign import CampaignContact
from app.providers.mock_provider import MockEmailProvider
from app.controllers.public_controller import TRANSPARENT_PNG_1X1


def test_open_tracking_pixel_injection_and_public_endpoint(db_session, client, user_a, monkeypatch):
    """
    Testa injeção do pixel de rastreamento no disparo e funcionamento da rota pública de tracking 1x1.
    """
    contact_service = ContactService(db_session)
    template_service = TemplateService(db_session)
    campaign_service = CampaignService(db_session)

    mock_provider = MockEmailProvider(sender_name=user_a.name, sender_email=user_a.email)
    monkeypatch.setattr(campaign_service.email_service, "get_provider", lambda uid: (mock_provider, None))

    # 1. Criar contato e template
    _, _, contact = contact_service.create_contact(user_a.id, "Carlos Cliente", "carlos@exemplo.com")
    _, _, template = template_service.create_template(
        user_id=user_a.id,
        name="Template Newsletter Aberta",
        header="<div><h1>Topo</h1></div>",
        body="<div><p>Olá, {{nome}}! Veja nossas ofertas.</p></div>",
        footer="<div><p>Rodapé</p></div>"
    )

    # 2. Criar e enviar campanha
    ok_c, _, campaign = campaign_service.create_campaign(
        user_id=user_a.id,
        name="Campanha Black Friday",
        subject="Super Ofertas Exclusivas",
        template_id=template.id,
        contact_ids=[contact.id]
    )
    assert ok_c is True

    recipient = db_session.query(CampaignContact).filter(CampaignContact.campaign_id == campaign.id).first()
    assert recipient is not None
    assert recipient.open_token is not None
    assert len(recipient.open_token) > 20
    assert recipient.opened_at is None
    assert recipient.open_count == 0

    # 3. Disparar campanha
    ok_send, _, _ = campaign_service.send_campaign(user_a.id, campaign.id, user_a, base_url="http://testserver")
    assert ok_send is True
    assert len(mock_provider.sent_emails) == 1

    # Verificar injeção da tag do pixel no HTML enviado
    sent_html = mock_provider.sent_emails[0]["html_content"]
    expected_pixel_src = f"http://testserver/track/open/{recipient.open_token}.png"
    assert expected_pixel_src in sent_html
    assert "<img" in sent_html

    # 4. Simular o cliente de e-mail carregando o pixel através da rota pública
    res = client.get(f"/track/open/{recipient.open_token}.png")
    assert res.status_code == 200
    assert res.headers["content-type"] == "image/png"
    assert res.content == TRANSPARENT_PNG_1X1
    assert "no-cache" in res.headers.get("cache-control", "")

    # Verificar atualização no banco
    db_session.refresh(recipient)
    db_session.refresh(campaign)
    assert recipient.opened_at is not None
    assert recipient.open_count == 1
    assert campaign.total_opened == 1

    # 5. Segunda abertura do mesmo destinatário (não deve inflar contatos únicos abertos)
    res2 = client.get(f"/track/open/{recipient.open_token}.png")
    assert res2.status_code == 200

    db_session.refresh(recipient)
    db_session.refresh(campaign)
    assert recipient.open_count == 2
    assert campaign.total_opened == 1

    # 6. Relatório deve refletir a taxa de abertura
    report = campaign_service.get_campaign_report(user_a.id, campaign.id)
    assert report["opened"] == 1
    assert report["open_rate"] == 100.0


def test_send_test_email_service_and_endpoint(db_session, client, user_a, monkeypatch):
    """
    Testa o envio de e-mail de prova/teste via service e via endpoint HTTP POST.
    """
    from app.services.email_service import EmailService

    contact_service = ContactService(db_session)
    template_service = TemplateService(db_session)
    campaign_service = CampaignService(db_session)

    mock_provider = MockEmailProvider(sender_name=user_a.name, sender_email=user_a.email)
    monkeypatch.setattr(EmailService, "get_provider", lambda self, uid: (mock_provider, None))

    _, _, template = template_service.create_template(
        user_id=user_a.id,
        name="Template Prova",
        header="<h1>Header</h1>",
        body="<p>Mensagem para {{nome}}</p>",
        footer="<p>Footer</p>"
    )
    _, _, contact = contact_service.create_contact(user_a.id, "Teste Dest", "teste@empresa.com")
    _, _, campaign = campaign_service.create_campaign(
        user_id=user_a.id,
        name="Campanha com Teste",
        subject="Novidade da Semana",
        template_id=template.id,
        contact_ids=[contact.id]
    )

    # 1. Envio de teste via Service com e-mail inválido
    ok_inv, msg_inv = campaign_service.send_test_email(user_a.id, campaign.id, "email_invalido", user_a)
    assert ok_inv is False
    assert "formato inválido" in msg_inv

    # 2. Envio de teste via Service com e-mail válido
    ok_test, msg_test = campaign_service.send_test_email(user_a.id, campaign.id, "destinatario_real@gmail.com", user_a)
    assert ok_test is True
    assert "com sucesso" in msg_test
    assert len(mock_provider.sent_emails) == 1
    assert mock_provider.sent_emails[0]["to_email"] == "destinatario_real@gmail.com"
    assert mock_provider.sent_emails[0]["subject"] == "[TESTE] Novidade da Semana"

    # 3. Envio via endpoint HTTP POST autenticado
    session_token = AuthService.create_session_token(user_a.id, getattr(user_a, "token_version", 1))
    client.cookies.set("session_token", session_token)

    response = client.post(
        f"/campaigns/{campaign.id}/test-send",
        data={"test_email": "outro_teste@empresa.com"},
        follow_redirects=False
    )
    assert response.status_code == 303
    assert "test_success" in response.headers["location"]


def test_test_send_multi_tenant_isolation(db_session, user_a, user_b, monkeypatch):
    """
    Garante que usuário B não pode enviar e-mail de teste de uma campanha pertencente ao usuário A.
    """
    contact_service = ContactService(db_session)
    template_service = TemplateService(db_session)
    campaign_service = CampaignService(db_session)

    mock_provider = MockEmailProvider(sender_name=user_a.name, sender_email=user_a.email)
    monkeypatch.setattr(campaign_service.email_service, "get_provider", lambda uid: (mock_provider, None))

    _, _, template = template_service.create_template(
        user_id=user_a.id,
        name="Template A",
        header="<h1>A</h1>",
        body="<p>Body</p>",
        footer="<p>Footer</p>"
    )
    _, _, contact = contact_service.create_contact(user_a.id, "Contato A", "a@empresa.com")
    _, _, campaign_a = campaign_service.create_campaign(
        user_id=user_a.id,
        name="Campanha User A",
        subject="Assunto User A",
        template_id=template.id,
        contact_ids=[contact.id]
    )

    # Usuário B tenta disparar teste na campanha do Usuário A
    ok, msg = campaign_service.send_test_email(user_b.id, campaign_a.id, "b@empresa.com", user_b)
    assert ok is False
    assert "não encontrada" in msg
