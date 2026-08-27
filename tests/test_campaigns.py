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
