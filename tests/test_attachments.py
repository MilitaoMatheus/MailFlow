import os
import pytest
from app.models.contact import ContactStatus
from app.models.campaign import CampaignStatus, CampaignContactStatus
from app.services.campaign_service import CampaignService
from app.services.contact_service import ContactService
from app.services.template_service import TemplateService
from app.providers.mock_provider import MockEmailProvider
from app.models.campaign_attachment import CampaignAttachment


def test_campaign_creation_with_attachments(db_session, user_a):
    """Testa a criação de campanha vinculada com anexos de arquivos no banco de dados."""
    contact_service = ContactService(db_session)
    template_service = TemplateService(db_session)
    campaign_service = CampaignService(db_session)

    # 1. Criar contato e template
    _, _, contact = contact_service.create_contact(user_a.id, "Gabriel Teste", "gabriel@gmail.com")
    _, _, template = template_service.create_template(
        user_id=user_a.id,
        name="Template Anexo",
        header="",
        body="Olá, segue currículo.",
        footer=""
    )

    # 2. Metadados dos anexos simulando salvamento no disco
    attachments_meta = [
        {
            "file_path": "C:/fake/path/curriculo.pdf",
            "file_name": "curriculo.pdf",
            "content_type": "application/pdf"
        },
        {
            "file_path": "C:/fake/path/portfolio.docx",
            "file_name": "portfolio.docx",
            "content_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        }
    ]

    # 3. Criar campanha com anexos
    ok, msg, campaign = campaign_service.create_campaign(
        user_id=user_a.id,
        name="Campanha com Currículo",
        subject="Vaga de Emprego",
        template_id=template.id,
        contact_ids=[contact.id],
        attachments_meta=attachments_meta
    )

    assert ok is True
    assert campaign.total_recipients == 1
    assert len(campaign.attachments) == 2

    # Verificar dados do anexo no banco
    att1 = campaign.attachments[0]
    assert att1.file_name == "curriculo.pdf"
    assert att1.file_path == "C:/fake/path/curriculo.pdf"
    assert att1.content_type == "application/pdf"

    att2 = campaign.attachments[1]
    assert att2.file_name == "portfolio.docx"


def test_campaign_dispatch_with_attachments(db_session, user_a, monkeypatch, tmp_path):
    """Testa se os anexos físicos são lidos e repassados ao provedor de e-mails no disparo."""
    contact_service = ContactService(db_session)
    template_service = TemplateService(db_session)
    campaign_service = CampaignService(db_session)

    # Configurar mock provider
    mock_provider = MockEmailProvider(sender_name="João", sender_email="joao@empresa.com")
    monkeypatch.setattr(campaign_service.email_service, "get_provider", lambda uid: (mock_provider, None))

    # Criar arquivo temporário físico no disco de testes
    temp_file1 = tmp_path / "curr.pdf"
    temp_file1.write_bytes(b"conteudo_do_pdf")
    
    temp_file2 = tmp_path / "port.txt"
    temp_file2.write_bytes(b"conteudo_do_portfolio")

    # 1. Criar contato e template
    _, _, contact = contact_service.create_contact(user_a.id, "Lucas Recrutador", "lucas@empresa.com")
    _, _, template = template_service.create_template(
        user_id=user_a.id,
        name="Template Vagas",
        header="",
        body="Olá, segue currículo anexo.",
        footer=""
    )

    attachments_meta = [
        {
            "file_path": str(temp_file1),
            "file_name": "curr.pdf",
            "content_type": "application/pdf"
        },
        {
            "file_path": str(temp_file2),
            "file_name": "port.txt",
            "content_type": "text/plain"
        }
    ]

    # 2. Criar campanha
    _, _, campaign = campaign_service.create_campaign(
        user_id=user_a.id,
        name="Campanha Vaga",
        subject="Assunto Vaga",
        template_id=template.id,
        contact_ids=[contact.id],
        attachments_meta=attachments_meta
    )

    # 3. Disparar
    ok_send, _, report = campaign_service.send_campaign(user_a.id, campaign.id, user_a)
    assert ok_send is True
    assert report["total_sent"] == 1

    # 4. Validar se os anexos foram passados ao MockProvider
    assert len(mock_provider.sent_emails) == 1
    sent = mock_provider.sent_emails[0]
    assert sent["to_email"] == "lucas@empresa.com"
    assert sent["attachments"] is not None
    assert len(sent["attachments"]) == 2
    assert sent["attachments"][0]["name"] == "curr.pdf"
    assert sent["attachments"][1]["name"] == "port.txt"
    assert sent["attachments"][0]["path"] == str(temp_file1)
