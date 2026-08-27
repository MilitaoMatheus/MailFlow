import pytest
from app.services.contact_service import ContactService
from app.services.template_service import TemplateService
from app.services.campaign_service import CampaignService
from app.services.email_service import EmailService


def test_strict_data_isolation_between_users(db_session, user_a, user_b):
    """
    Testa o isolamento rigoroso de dados entre perfis distintos:
    Usuário A (João) vs Usuário B (Maria).
    """
    contact_service = ContactService(db_session)
    template_service = TemplateService(db_session)
    campaign_service = CampaignService(db_session)
    email_service = EmailService(db_session)

    # 1. João cria contatos e templates
    ok_ca, _, contact_a = contact_service.create_contact(
        user_id=user_a.id,
        name="Contato Exclusivo do João",
        email="cliente.joao@gmail.com"
    )
    assert ok_ca is True

    ok_ta, _, template_a = template_service.create_template(
        user_id=user_a.id,
        name="Template do João",
        header="<h1>Header João</h1>",
        body="<p>Body João</p>",
        footer="<p>Footer João</p>"
    )
    assert ok_ta is True

    # 2. Maria cria contatos e templates
    ok_cb, _, contact_b = contact_service.create_contact(
        user_id=user_b.id,
        name="Contato Exclusivo da Maria",
        email="cliente.maria@gmail.com"
    )
    assert ok_cb is True

    ok_tb, _, template_b = template_service.create_template(
        user_id=user_b.id,
        name="Template da Maria",
        header="<h1>Header Maria</h1>",
        body="<p>Body Maria</p>",
        footer="<p>Footer Maria</p>"
    )
    assert ok_tb is True

    # --- VERIFICAÇÃO DE ISOLAMENTO DE CONTATOS ---
    # João NÃO deve listar os contatos de Maria
    joao_contacts = contact_service.list_contacts(user_a.id)["contacts"]
    joao_emails = [c.email for c in joao_contacts]
    assert "cliente.joao@gmail.com" in joao_emails
    assert "cliente.maria@gmail.com" not in joao_emails

    # Maria NÃO deve conseguir buscar diretamente o contato de João por ID
    assert contact_service.get_contact(user_b.id, contact_a.id) is None
    # João NÃO deve conseguir buscar diretamente o contato de Maria por ID
    assert contact_service.get_contact(user_a.id, contact_b.id) is None

    # João NÃO deve conseguir editar ou excluir o contato de Maria
    ok_edit, _, _ = contact_service.update_contact(user_a.id, contact_b.id, "Hacked", "hacked@email.com")
    assert ok_edit is False
    ok_del, _ = contact_service.delete_contact(user_a.id, contact_b.id)
    assert ok_del is False

    # --- VERIFICAÇÃO DE ISOLAMENTO DE TEMPLATES ---
    # João NÃO deve listar os templates de Maria
    joao_templates = template_service.list_templates(user_a.id)
    joao_template_names = [t.name for t in joao_templates]
    assert "Template do João" in joao_template_names
    assert "Template da Maria" not in joao_template_names

    # Maria NÃO deve conseguir acessar template de João por ID
    assert template_service.get_template(user_b.id, template_a.id) is None
    # João NÃO deve conseguir atualizar template de Maria
    ok_t_edit, _, _ = template_service.update_template(user_a.id, template_b.id, "Hack", "H", "B", "F")
    assert ok_t_edit is False

    # --- VERIFICAÇÃO DE ISOLAMENTO DE CAMPANHAS ---
    # João cria uma campanha usando seu próprio template
    ok_camp_a, _, camp_a = campaign_service.create_campaign(
        user_id=user_a.id,
        name="Campanha do João",
        subject="Novidades do João",
        template_id=template_a.id,
        contact_ids=[contact_a.id]
    )
    assert ok_camp_a is True

    # Maria NÃO deve listar nem acessar a campanha de João
    maria_camps = campaign_service.list_campaigns(user_b.id)["campaigns"]
    assert len(maria_camps) == 0
    assert campaign_service.get_campaign(user_b.id, camp_a.id) is None
    assert campaign_service.get_campaign_report(user_b.id, camp_a.id) is None

    # Maria NÃO deve conseguir criar campanha utilizando o template de João
    ok_camp_b_hack, _, _ = campaign_service.create_campaign(
        user_id=user_b.id,
        name="Campanha Invasora",
        subject="Tentativa",
        template_id=template_a.id,
        contact_ids=[contact_b.id]
    )
    assert ok_camp_b_hack is False

    # --- VERIFICAÇÃO DE ISOLAMENTO DE CONFIGURAÇÕES SMTP ---
    smtp_joao = email_service.get_smtp_account(user_a.id)
    smtp_maria = email_service.get_smtp_account(user_b.id)
    assert smtp_joao.smtp_host == "smtp.empresa.com"
    assert smtp_maria.smtp_host == "smtp.maria.com"
    assert smtp_joao.email != smtp_maria.email
